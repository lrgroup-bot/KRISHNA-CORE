from krishna_core.krishna_observability import KrishnaObservability

def test_span_correlates_and_measures_latency(tmp_path):
    o=KrishnaObservability(tmp_path)
    with o.span("BRAHMAGYAN","verify",mission_id="m1") as s:
        assert s["trace_id"] and s["span_id"]
    summary=o.latency_summary()
    assert summary["BRAHMAGYAN:verify"]["count"]==1
    rows=o.log.read_text(encoding="utf-8").splitlines()
    assert len(rows)==2

def test_failed_span_is_recorded_and_reraised(tmp_path):
    import pytest,json
    o=KrishnaObservability(tmp_path)
    with pytest.raises(RuntimeError):
        with o.span("SURYDEV","collect"):
            raise RuntimeError("secret detail must not be logged")
    row=json.loads(o.log.read_text(encoding="utf-8").splitlines()[-1])
    assert row["status"]=="failed" and row["metrics"]["error_type"]=="RuntimeError"
    assert "secret detail" not in str(row)
