"""Vector index storage using FAISS with pure NumPy cosine fallback."""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False


class AnalogIndex:
    """Vector index storing event embeddings with FAISS (and pure NumPy cosine fallback)."""

    def __init__(self, dim: int = 16, prefer_faiss: bool = True) -> None:
        self.dim = dim
        self.prefer_faiss = prefer_faiss and FAISS_AVAILABLE
        self.index_backend = "faiss" if self.prefer_faiss else "numpy"
        self.faiss_index: Optional[Any] = None
        self.indexed_embeddings: Optional[np.ndarray] = None
        self.events: List[Dict[str, Any]] = []

    def build(self, embeddings: np.ndarray, events: List[Dict[str, Any]]) -> None:
        """Build index from normalized embeddings and event metadata."""
        self.events = events
        self.indexed_embeddings = np.ascontiguousarray(embeddings, dtype=np.float32)

        # Normalize indexed embeddings to unit length for cosine similarity
        norms = np.linalg.norm(self.indexed_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.indexed_embeddings = self.indexed_embeddings / norms

        if self.prefer_faiss:
            try:
                # Cosine similarity via Inner Product on L2-normalized embeddings
                self.faiss_index = faiss.IndexFlatIP(self.dim)
                self.faiss_index.add(self.indexed_embeddings)
                self.index_backend = "faiss"
                return
            except Exception as e:
                print(f"[!] FAISS initialization failed ({e}), falling back to NumPy cosine search.")

        self.index_backend = "numpy"

    def search(self, query_embedding: np.ndarray, k: int = 3) -> List[Tuple[float, Dict[str, Any]]]:
        """Search top-k nearest events. Returns list of (similarity_score [0..1], event_dict)."""
        k = min(k, len(self.events))
        q = np.ascontiguousarray(query_embedding.reshape(1, -1), dtype=np.float32)

        # Ensure normalized query
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        results = []
        if self.index_backend == "faiss" and self.faiss_index is not None:
            distances, indices = self.faiss_index.search(q, k)
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self.events):
                    continue
                # Inner product of unit vectors in [-1, 1], map to [0, 1]
                sim = float(np.clip((dist + 1.0) / 2.0, 0.0, 1.0))
                results.append((sim, self.events[idx]))
        else:
            if self.indexed_embeddings is None:
                raise RuntimeError("Index has not been built.")
            # Pure NumPy cosine similarity: dot product of normalized vectors
            sims = np.dot(q, self.indexed_embeddings.T)[0]
            top_indices = np.argsort(-sims)[:k]
            for idx in top_indices:
                sim = float(np.clip((sims[idx] + 1.0) / 2.0, 0.0, 1.0))
                results.append((sim, self.events[idx]))

        return results
