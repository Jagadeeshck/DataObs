"""Evidence-first historical incident intelligence owned by Team 3."""

from .features import FEATURE_VERSION, IncidentFeatures, extract_features
from .fingerprint import incident_fingerprint
from .similarity import SCORING_VERSION, score_similarity

__all__ = [
    "FEATURE_VERSION",
    "SCORING_VERSION",
    "IncidentFeatures",
    "extract_features",
    "incident_fingerprint",
    "score_similarity",
]
