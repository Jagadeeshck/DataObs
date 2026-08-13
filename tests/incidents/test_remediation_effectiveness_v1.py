from datetime import datetime, timezone

from services.incident_manager.effectiveness.classifier import classify
from services.incident_manager.effectiveness.metrics import summarize
from services.incident_manager.effectiveness.models import (
    EFFECTIVENESS_DEFINITION_VERSION,
    EffectivenessClass,
    EvidenceCoverage,
    InterventionType,
    ProviderStatus,
    RemediationEpisode,
    VerificationStatus,
    episode_identity,
)


def episode(verification=VerificationStatus.UNAVAILABLE, provider=ProviderStatus.SUCCESS, **changes):
    effectiveness = classify(provider, verification)
    evidence = EvidenceCoverage(
        execution_evidence=True,
        provider_evidence=True,
        verification_evidence=verification != VerificationStatus.UNAVAILABLE,
        recovery_evidence=False,
        stability_evidence=False,
        recurrence_evidence=False,
    )
    values = dict(
        episode_id=episode_identity("t", "prod", "i", "e", EFFECTIVENESS_DEFINITION_VERSION),
        tenant_id="t",
        environment="prod",
        incident_id="i",
        intervention_type=InterventionType.SAFE_REMEDIATION_ACTION,
        intervention_id="restart",
        execution_id="e",
        action_catalog_id="restart",
        action_catalog_version="2",
        provider_status=provider,
        verification_status=verification,
        effectiveness_class=effectiveness,
        evidence=evidence,
        evidence_coverage=evidence.coverage,
        source_incident_revision="2:1",
        source_execution_revision="4",
        computed_at=datetime.now(timezone.utc),
    )
    values.update(changes)
    return RemediationEpisode(**values)


def test_provider_success_is_not_verified_effect():
    assert classify(ProviderStatus.SUCCESS, VerificationStatus.UNAVAILABLE) == EffectivenessClass.INCONCLUSIVE


def test_verification_success_can_create_verified_effect():
    assert classify(ProviderStatus.SUCCESS, VerificationStatus.VERIFIED) == EffectivenessClass.VERIFIED_EFFECTIVE


def test_verification_failure_creates_no_observed_effect():
    assert classify(ProviderStatus.SUCCESS, VerificationStatus.FAILED) == EffectivenessClass.NO_OBSERVED_EFFECT


def test_unknown_provider_outcome_stays_unknown():
    assert classify(ProviderStatus.TIMEOUT, VerificationStatus.UNAVAILABLE) == EffectivenessClass.OUTCOME_UNKNOWN


def test_missing_verification_is_not_failure():
    assert episode().effectiveness_class != EffectivenessClass.FAILED


def test_recovery_after_action_is_temporal_association():
    item = episode(recovery_association_observed=True, recovery_after_action_ms=3000)
    assert item.effectiveness_class == EffectivenessClass.INCONCLUSIVE


def test_multiple_interventions_reduce_attribution_certainty():
    item = episode(VerificationStatus.VERIFIED, actions_after_episode_before_recovery=2, attribution_ambiguous=True)
    assert item.attribution_ambiguous and item.effectiveness_class == EffectivenessClass.VERIFIED_EFFECTIVE


def test_reopen_and_recurrence_do_not_rewrite_historical_verification():
    item = episode(VerificationStatus.VERIFIED, incident_reopened_after=True, recurrence_observed=True)
    assert item.effectiveness_class == EffectivenessClass.VERIFIED_EFFECTIVE


def test_effectiveness_definition_version_and_episode_identity_are_deterministic():
    assert episode().effectiveness_definition_version == EFFECTIVENESS_DEFINITION_VERSION
    assert episode().episode_id == episode().episode_id


def test_verified_effect_rate_uses_verification_eligible_denominator_and_exposes_coverage():
    result = summarize([episode(VerificationStatus.VERIFIED), episode(VerificationStatus.FAILED), episode()])
    assert result.verification_eligible_count == 2
    assert result.verification_coverage == 2 / 3
    assert result.verified_effect_rate == 0.5


def test_percentiles_include_sample_count():
    result = summarize([episode(VerificationStatus.VERIFIED, time_to_verified_effect_ms=1000), episode()])
    assert result.time_to_effect_sample_count == 1
