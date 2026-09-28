"""Embedding extractors for storm event windows: Handcrafted normalized features and PyTorch Autoencoder."""

from typing import Dict, Any, List, Union, Tuple, Optional
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

EMBEDDING_DIM = 16
SAVED_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "saved"


def _extract_raw_input_vector(event: Dict[str, Any]) -> np.ndarray:
    """Extract standard 80-dimensional input vector (72h rainfall + 8 geotechnical features)."""
    # 72h rainfall series
    rain_series = event.get("approx_rainfall_72h_series") or event.get("rainfall_72h") or [0.0] * 72
    if len(rain_series) < 72:
        rain_series = [0.0] * (72 - len(rain_series)) + list(rain_series)
    elif len(rain_series) > 72:
        rain_series = list(rain_series[-72:])
    rain_arr = np.array(rain_series, dtype=np.float32) / 80.0  # normalize

    # 8 geotechnical & terrain features
    geo_features = np.array([
        float(event.get("antecedent_moisture", 0.45)),
        float(event.get("slope", 30.0)) / 60.0,
        float(event.get("elevation", 1600.0)) / 4000.0,
        np.sin(np.radians(float(event.get("aspect", 180.0)))),
        float(event.get("curvature", 0.0)) * 10.0,
        float(event.get("upstream_catchment_area", 35.0)) / 100.0,
        float(event.get("distance_to_stream", 50.0)) / 200.0,
        float(event.get("factor_of_safety", 1.2)) / 2.5,
    ], dtype=np.float32)

    return np.concatenate([rain_arr, geo_features])


class HandcraftedEmbedder:
    """Extracts a normalized 16-dimensional summary embedding vector from a storm window."""

    def __init__(self) -> None:
        self.dim = EMBEDDING_DIM

    def embed(self, event: Dict[str, Any]) -> np.ndarray:
        """Compute normalized 16-D feature vector."""
        rain_series = event.get("approx_rainfall_72h_series") or event.get("rainfall_72h") or [0.0] * 72
        if len(rain_series) < 72:
            rain_series = [0.0] * (72 - len(rain_series)) + list(rain_series)
        elif len(rain_series) > 72:
            rain_series = list(rain_series[-72:])
        rain_arr = np.array(rain_series, dtype=float)

        total_72h = float(np.sum(rain_arr))
        # Rolling peaks
        r24_max = float(np.max([np.sum(rain_arr[max(0, i-24):i]) for i in range(1, 73)])) if len(rain_arr) >= 24 else total_72h
        r6_max = float(np.max([np.sum(rain_arr[max(0, i-6):i]) for i in range(1, 73)])) if len(rain_arr) >= 6 else total_72h
        r3_max = float(np.max([np.sum(rain_arr[max(0, i-3):i]) for i in range(1, 73)])) if len(rain_arr) >= 3 else total_72h
        r1_max = float(np.max(rain_arr)) if len(rain_arr) > 0 else 0.0

        # Centroid hour (temporal location of storm burst)
        hours = np.arange(1, 73)
        centroid = float(np.sum(hours * rain_arr) / max(total_72h, 1e-4)) / 72.0
        burst_ratio = float(r3_max / max(total_72h, 1.0))

        # Terrain & physics features
        m = float(event.get("antecedent_moisture", 0.45))
        slope = float(event.get("slope", 30.0)) / 60.0
        elev = float(event.get("elevation", 1600.0)) / 4000.0
        aspect = float(event.get("aspect", 180.0))
        curv = float(event.get("curvature", 0.0)) * 10.0
        catch = float(event.get("upstream_catchment_area", 35.0)) / 100.0
        dist_stream = float(event.get("distance_to_stream", 50.0)) / 200.0
        fs = float(event.get("factor_of_safety", 1.2)) / 2.5

        vector = np.array([
            total_72h / 300.0,
            r24_max / 150.0,
            r6_max / 80.0,
            r3_max / 50.0,
            r1_max / 25.0,
            centroid,
            burst_ratio,
            m,
            slope,
            elev,
            np.sin(np.radians(aspect)),
            np.cos(np.radians(aspect)),
            curv,
            catch,
            dist_stream,
            fs,
        ], dtype=np.float32)

        # L2 normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def embed_dataframe(self, df: Any) -> np.ndarray:
        """Fast vectorized batch embedding for tabular DataFrame records."""
        n = len(df)
        total_72h = df["rain_72h"].values if "rain_72h" in df.columns else np.zeros(n, dtype=np.float32)
        r24_max = df["rain_24h"].values if "rain_24h" in df.columns else np.zeros(n, dtype=np.float32)
        r6_max = df["rain_6h"].values if "rain_6h" in df.columns else np.zeros(n, dtype=np.float32)
        r3_max = df["rain_3h"].values if "rain_3h" in df.columns else np.zeros(n, dtype=np.float32)
        r1_max = df["rain_1h"].values if "rain_1h" in df.columns else np.zeros(n, dtype=np.float32)

        centroid = np.full(n, 0.65, dtype=np.float32)
        burst_ratio = r3_max / np.maximum(total_72h, 1.0)

        m = df["antecedent_moisture"].values if "antecedent_moisture" in df.columns else np.full(n, 0.45, dtype=np.float32)
        slope = (df["slope"].values / 60.0) if "slope" in df.columns else np.full(n, 0.5, dtype=np.float32)
        elev = (df["elevation"].values / 4000.0) if "elevation" in df.columns else np.full(n, 0.4, dtype=np.float32)
        aspect = df["aspect"].values if "aspect" in df.columns else np.full(n, 180.0, dtype=np.float32)
        curv = (df["curvature"].values * 10.0) if "curvature" in df.columns else np.zeros(n, dtype=np.float32)
        catch = (df["upstream_catchment_area"].values / 100.0) if "upstream_catchment_area" in df.columns else np.full(n, 0.35, dtype=np.float32)
        dist_stream = (df["distance_to_stream"].values / 200.0) if "distance_to_stream" in df.columns else np.full(n, 0.25, dtype=np.float32)
        fs = (df["factor_of_safety"].values / 2.5) if "factor_of_safety" in df.columns else np.full(n, 0.5, dtype=np.float32)

        matrix = np.column_stack([
            total_72h / 300.0,
            r24_max / 150.0,
            r6_max / 80.0,
            r3_max / 50.0,
            r1_max / 25.0,
            centroid,
            burst_ratio,
            m,
            slope,
            elev,
            np.sin(np.radians(aspect)),
            np.cos(np.radians(aspect)),
            curv,
            catch,
            dist_stream,
            fs,
        ]).astype(np.float32)

        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms



class AutoencoderNet(nn.Module):
    """Small PyTorch feedforward autoencoder for storm event representation learning."""

    def __init__(self, input_dim: int = 80, latent_dim: int = 16) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 48),
            nn.ReLU(),
            nn.Linear(48, 28),
            nn.ReLU(),
            nn.Linear(28, latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 28),
            nn.ReLU(),
            nn.Linear(28, 48),
            nn.ReLU(),
            nn.Linear(48, input_dim),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        latent = self.encoder(x)
        reconstruction = self.decoder(latent)
        return latent, reconstruction


class PyTorchAutoencoderEmbedder:
    """PyTorch Autoencoder trained to project 80-D storm windows into a 16-D latent manifold."""

    def __init__(self, latent_dim: int = 16) -> None:
        self.latent_dim = latent_dim
        self.net = AutoencoderNet(input_dim=80, latent_dim=latent_dim)
        self.is_fitted = False

    def fit(self, events: List[Dict[str, Any]], epochs: int = 40, lr: float = 0.005) -> float:
        """Fit autoencoder on a collection of event dictionaries."""
        X = np.stack([_extract_raw_input_vector(e) for e in events])
        tensor_X = torch.tensor(X, dtype=torch.float32)

        optimizer = optim.Adam(self.net.parameters(), lr=lr)
        criterion = nn.MSELoss()

        self.net.train()
        final_loss = 0.0
        for _ in range(epochs):
            optimizer.zero_grad()
            _, recon = self.net(tensor_X)
            loss = criterion(recon, tensor_X)
            loss.backward()
            optimizer.step()
            final_loss = float(loss.item())

        self.is_fitted = True
        return final_loss

    def embed(self, event: Dict[str, Any]) -> np.ndarray:
        """Generate 16-D latent embedding."""
        raw_vec = _extract_raw_input_vector(event)
        tensor_in = torch.tensor(raw_vec, dtype=torch.float32).unsqueeze(0)
        self.net.eval()
        with torch.no_grad():
            latent = self.net.encoder(tensor_in).squeeze(0).numpy()
        norm = np.linalg.norm(latent)
        if norm > 0:
            latent = latent / norm
        return latent.astype(np.float32)

    def save(self, path: Optional[Path] = None) -> Path:
        """Save autoencoder weights."""
        p = path or (SAVED_MODEL_DIR / "analog_autoencoder.pt")
        p.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.net.state_dict(), p)
        return p

    def load(self, path: Optional[Path] = None) -> None:
        """Load autoencoder weights."""
        p = path or (SAVED_MODEL_DIR / "analog_autoencoder.pt")
        if p.exists():
            self.net.load_state_dict(torch.load(p, weights_only=True))
            self.is_fitted = True


def compare_embedding_methods(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare Handcrafted Normalized Embeddings vs PyTorch Autoencoder."""
    handcrafted = HandcraftedEmbedder()
    autoencoder = PyTorchAutoencoderEmbedder(latent_dim=16)
    final_loss = autoencoder.fit(events, epochs=35)

    hc_embeddings = np.stack([handcrafted.embed(e) for e in events])
    ae_embeddings = np.stack([autoencoder.embed(e) for e in events])

    # Compute correlation / mean distance between embedding spaces
    hc_cos = np.dot(hc_embeddings, hc_embeddings.T)
    ae_cos = np.dot(ae_embeddings, ae_embeddings.T)
    pairwise_corr = float(np.corrcoef(hc_cos.flatten(), ae_cos.flatten())[0, 1])

    return {
        "num_events_evaluated": len(events),
        "embedding_dimension": EMBEDDING_DIM,
        "autoencoder_final_reconstruction_mse": round(final_loss, 6),
        "embedding_space_pairwise_correlation": round(pairwise_corr, 4),
        "summary": (
            f"Evaluated {len(events)} events across 16-D handcrafted and autoencoder embeddings. "
            f"Autoencoder converged to MSE {final_loss:.6f} with pairwise similarity alignment of {pairwise_corr:.2f}."
        ),
    }
