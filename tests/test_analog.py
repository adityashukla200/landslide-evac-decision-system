"""Unit tests for /ml/analog case-based retrieval and explainability module."""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from ml.analog.library import get_analog_library, build_historical_reconstructions, build_synthetic_analogs
from ml.analog.embeddings import HandcraftedEmbedder, PyTorchAutoencoderEmbedder, compare_embedding_methods
from ml.analog.index import AnalogIndex
from ml.analog.matcher import AnalogMatcher, find_analogs, compute_dtw_distance
from ml.analog.blend import AnalogModelBlender, evaluate_analog_blend
from ml.models.base_model import LandslideRiskModel


def test_analog_library_content_and_provenance():
    """Verify analog library size >= 50, historical reconstructions presence, and strict provenance labeling."""
    library = get_analog_library()
    assert len(library) >= 50

    # Historical disasters check
    historical_ids = {"HIST_KEDARNATH_2013", "HIST_CHAMOLI_2021", "HIST_WAYANAD_2024", "HIST_MANDI_2023"}
    found_ids = {e["event_id"] for e in library if e["event_id"] in historical_ids}
    assert found_ids == historical_ids

    for event in library:
        assert "provenance" in event
        assert "outcome" in event
        assert "landslide" in event["outcome"]
        assert "damage_scale" in event["outcome"]
        assert len(event["approx_rainfall_72h_series"]) == 72

        if event["event_id"] in historical_ids:
            assert event["provenance"] == "approximate reconstruction from public reports, not observed data"
            assert "approximate" in str(event["approx_rainfall_24h_mm"]).lower()
        else:
            assert event["provenance"] == "synthetic"
            assert "synthetic" in str(event["approx_rainfall_24h_mm"]).lower()


def test_handcrafted_and_autoencoder_embeddings():
    """Test HandcraftedEmbedder and PyTorchAutoencoderEmbedder vector dimensions and normalization."""
    library = get_analog_library()
    sample = library[0]

    # Handcrafted Embedder
    hc = HandcraftedEmbedder()
    vec_hc = hc.embed(sample)
    assert len(vec_hc) == 16
    assert abs(np.linalg.norm(vec_hc) - 1.0) < 1e-4

    # PyTorch Autoencoder Embedder
    ae = PyTorchAutoencoderEmbedder(latent_dim=16)
    loss = ae.fit(library[:15], epochs=15)
    assert loss >= 0.0

    vec_ae = ae.embed(sample)
    assert len(vec_ae) == 16
    assert abs(np.linalg.norm(vec_ae) - 1.0) < 1e-4

    # Embedding comparison
    comp = compare_embedding_methods(library[:20])
    assert comp["num_events_evaluated"] == 20
    assert "autoencoder_final_reconstruction_mse" in comp
    assert "embedding_space_pairwise_correlation" in comp


def test_analog_index_backends():
    """Test AnalogIndex query retrieval under FAISS and pure NumPy fallback."""
    library = get_analog_library()[:10]
    hc = HandcraftedEmbedder()
    embeds = np.stack([hc.embed(e) for e in library])

    # 1. FAISS or active backend
    idx = AnalogIndex(dim=16, prefer_faiss=True)
    idx.build(embeds, library)
    results = idx.search(embeds[0], k=3)
    assert len(results) == 3
    assert results[0][0] >= 0.99  # Top match is itself

    # 2. Force NumPy fallback
    idx_np = AnalogIndex(dim=16, prefer_faiss=False)
    idx_np.build(embeds, library)
    results_np = idx_np.search(embeds[0], k=3)
    assert len(results_np) == 3
    assert results_np[0][0] >= 0.99
    assert results_np[0][1]["event_id"] == results[0][1]["event_id"]


def test_find_analogs_and_dtw_matching():
    """Test AnalogMatcher retrieval with both vector embeddings and DTW hyetograph matching."""
    matcher = AnalogMatcher()
    sample_state = {
        "rain_1h": 22.0,
        "rain_3h": 48.0,
        "rain_6h": 70.0,
        "rain_24h": 125.0,
        "rain_72h": 180.0,
        "antecedent_moisture": 0.85,
        "elevation": 2400.0,
        "slope": 40.0,
        "aspect": 190.0,
        "curvature": 0.03,
        "upstream_catchment_area": 50.0,
        "distance_to_stream": 30.0,
        "factor_of_safety": 0.74,
    }

    # Vector search (Autoencoder)
    analogs_ae = matcher.find_analogs(sample_state, k=3, method="embedding", embedding_type="autoencoder")
    assert len(analogs_ae) == 3
    for a in analogs_ae:
        assert 0.0 <= a["similarity_pct"] <= 100.0
        assert "name" in a
        assert "date" in a
        assert "location" in a
        assert "outcome" in a
        assert "reason" in a
        assert "provenance" in a

    # Vector search (Handcrafted)
    analogs_hc = matcher.find_analogs(sample_state, k=3, method="embedding", embedding_type="handcrafted")
    assert len(analogs_hc) == 3

    # DTW Hyetograph search
    analogs_dtw = matcher.find_analogs(sample_state, k=3, method="dtw")
    assert len(analogs_dtw) == 3
    for a in analogs_dtw:
        assert 0.0 <= a["similarity_pct"] <= 100.0


def test_dtw_distance_properties():
    """Test that DTW distance is zero for identical sequences and positive for differing sequences."""
    s1 = np.array([0, 5, 20, 45, 10, 2], dtype=float)
    s2 = np.array([0, 5, 20, 45, 10, 2], dtype=float)
    s3 = np.array([0, 0, 2, 5, 20, 45], dtype=float)

    assert compute_dtw_distance(s1, s2) == 0.0
    assert compute_dtw_distance(s1, s3) > 0.0


def test_explanation_json_format():
    """Verify explanation_json matches required schema: {"top_analogs": [...], "key_drivers": [...]}."""
    sample_state = {
        "rain_3h": 45.0,
        "rain_24h": 120.0,
        "slope": 38.0,
        "factor_of_safety": 0.78,
        "antecedent_moisture": 0.82,
        "distance_to_stream": 25.0,
    }
    matcher = AnalogMatcher()
    explanation = matcher.build_explanation_json(sample_state, k=3)

    assert "top_analogs" in explanation
    assert "key_drivers" in explanation
    assert len(explanation["top_analogs"]) == 3
    assert len(explanation["key_drivers"]) >= 3
    for driver in explanation["key_drivers"]:
        assert "factor" in driver
        assert "value" in driver
        assert "status" in driver
        assert "description" in driver


def test_analog_model_blender_fit_and_evaluate():
    """Test AnalogModelBlender optimization and evaluate_analog_blend metrics."""
    # Synthetic calibration and test data
    np.random.seed(42)
    n = 200
    calib_df = pd.DataFrame({
        "time": pd.date_range("2022-06-01", periods=n, freq="h"),
        "rain_1h": np.random.uniform(0, 10, n),
        "rain_3h": np.random.uniform(0, 25, n),
        "rain_6h": np.random.uniform(0, 40, n),
        "rain_24h": np.random.uniform(0, 80, n),
        "rain_72h": np.random.uniform(0, 120, n),
        "antecedent_moisture": np.random.uniform(0.2, 0.8, n),
        "elevation": np.random.uniform(1000, 2500, n),
        "slope": np.random.uniform(15, 45, n),
        "aspect": np.random.uniform(0, 360, n),
        "curvature": np.random.uniform(-0.02, 0.02, n),
        "upstream_catchment_area": np.random.uniform(10, 80, n),
        "distance_to_stream": np.random.uniform(20, 150, n),
        "ndvi": np.random.uniform(0.3, 0.7, n),
        "factor_of_safety": np.random.uniform(0.7, 1.8, n),
        "landslide_within_6h": (np.random.rand(n) < 0.05).astype(int),
    })

    test_df = calib_df.copy()

    # Mock base model
    class MockModel:
        def predict_proba(self, df):
            return np.full(len(df), 0.05, dtype=np.float32)

    mock_model = MockModel()
    results = evaluate_analog_blend(calib_df, test_df, mock_model, p_clim=0.05, k=3)

    assert "optimal_alpha" in results
    assert 0.80 <= results["optimal_alpha"] <= 1.0
    assert "base_model_brier_score" in results
    assert "blended_model_brier_score" in results
    assert "honest_assessment" in results
    assert isinstance(results["improved_brier"], bool)
