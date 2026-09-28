"""Case-based analog explainable prediction and hyetograph matching module."""

from ml.analog.library import get_analog_library, build_historical_reconstructions, build_synthetic_analogs
from ml.analog.embeddings import HandcraftedEmbedder, PyTorchAutoencoderEmbedder, compare_embedding_methods
from ml.analog.index import AnalogIndex
from ml.analog.matcher import AnalogMatcher, get_analog_matcher, find_analogs, compute_dtw_distance
from ml.analog.blend import AnalogModelBlender, evaluate_analog_blend

__all__ = [
    "get_analog_library",
    "build_historical_reconstructions",
    "build_synthetic_analogs",
    "HandcraftedEmbedder",
    "PyTorchAutoencoderEmbedder",
    "compare_embedding_methods",
    "AnalogIndex",
    "AnalogMatcher",
    "get_analog_matcher",
    "find_analogs",
    "compute_dtw_distance",
    "AnalogModelBlender",
    "evaluate_analog_blend",
]
