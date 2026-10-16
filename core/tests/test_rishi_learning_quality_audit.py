"""Read-only Rishi evidence-quality audit regression tests."""
from krishna_core.rishi_council import RishiCouncil
from krishna_core.rishi_learning import RishiLearningLedger


def test_learning_quality_audit_does_not_claim_empty_memory_is_verified(tmp_path):
    council=RishiCouncil()
    ledger=RishiLearningLedger(tmp_path / "rishi-learning", council)
    result=ledger.learning_quality_audit()
    assert result["rishi_count"] == len(council.list())
    assert result["read_only"] is True
    assert all(row["diagnosis"] == "NO_FINDINGS" for row in result["results"])
    assert all(row["verified_fraction"] is None for row in result["results"])


def test_learning_quality_audit_distinguishes_provisional_and_verified(tmp_path):
    council=RishiCouncil()
    ledger=RishiLearningLedger(tmp_path / "rishi-learning", council)
    ledger.record_finding("gautama", "test methods", "Hypothesis pending",
                          maturity="L0", evidence_status="unknown", source_count=0)
    ledger.record_finding("gautama", "test methods", "Independent replication",
                          maturity="L6", evidence_status="verified", source_count=2)
    row=ledger.learning_quality_audit("gautama")["results"][0]
    assert row["total_findings"] == 2
    assert row["verified_findings"] == 1
    assert row["provisional_findings"] == 1
    assert row["insufficient_source_findings"] == 1
    assert row["diagnosis"] == "REVIEW_REQUIRED"
    assert row["verified_fraction"] == 0.5
