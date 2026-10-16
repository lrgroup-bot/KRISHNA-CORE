import unittest
from contextlib import contextmanager

class _Raises:
    def __init__(self, exception): self.exception=exception
    def __enter__(self): return self
    def __exit__(self, kind, value, traceback):
        if kind is None: raise AssertionError(f'Expected {self.exception.__name__}')
        return issubclass(kind,self.exception)

class _PytestCompat:
    raises=staticmethod(_Raises)

pytest=_PytestCompat()
from krishna_core.external_learning_ledger import ExternalLearningLedger


def test_capture_is_idempotent_and_requires_approval(tmp_path):
    ledger = ExternalLearningLedger(tmp_path / "learning.db")
    data = dict(source_url="https://github.com/example/project", source_revision="abc123",
                license_id="MIT", summary="Bounded task scheduling", evidence="Reviewed public source")
    first = ledger.capture(**data)
    assert first == ledger.capture(**data)
    assert first["status"] == "quarantined"
    assert ledger.approved() == []
    with pytest.raises(ValueError):
        ledger.capture(**{**data, "source_url": "http://github.com/example/project"})
    with pytest.raises(ValueError):
        ledger.capture(**{**data, "source_url": "https://user:password@example.com/private"})
    result = ledger.review(first["id"], reviewer="owner", tests_passed=True,
                           provenance_verified=True, license_verified=True, approved=True)
    assert result["status"] == "approved"
    assert len(ledger.approved()) == 1
    with pytest.raises(ValueError):
        ledger.review(first["id"], reviewer="other", approved=True)
    ledger.close()


def test_incomplete_verification_rejects_promotion(tmp_path):
    ledger = ExternalLearningLedger(tmp_path / "learning.db")
    item = ledger.capture(source_url="https://example.org/paper", source_revision="v1",
                          license_id="unknown", summary="Possible technique",
                          evidence="Single unverified source")
    result = ledger.review(item["id"], reviewer="auditor", approved=True,
                           tests_passed=True, provenance_verified=True)
    assert result["status"] == "rejected"
    assert ledger.approved() == []
    ledger.close()
