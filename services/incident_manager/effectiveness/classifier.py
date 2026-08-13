from .models import EffectivenessClass, ProviderStatus, VerificationStatus


def classify(provider: ProviderStatus, verification: VerificationStatus) -> EffectivenessClass:
    """Classify target effect; lifecycle timing never substitutes for verification."""
    if provider in {ProviderStatus.UNKNOWN, ProviderStatus.TIMEOUT, ProviderStatus.RECONCILIATION_REQUIRED}:
        return EffectivenessClass.OUTCOME_UNKNOWN
    if provider in {ProviderStatus.FAILED, ProviderStatus.CANCELLED}:
        return EffectivenessClass.FAILED
    if verification == VerificationStatus.VERIFIED:
        return EffectivenessClass.VERIFIED_EFFECTIVE
    if verification == VerificationStatus.FAILED:
        return EffectivenessClass.NO_OBSERVED_EFFECT
    if verification == VerificationStatus.CONTRADICTED:
        return EffectivenessClass.CONTRADICTED
    return EffectivenessClass.INCONCLUSIVE
