from krishna_core.security_soc import DefensiveSOC, SecurityEvent

def test_soc_normalizes_and_correlates_repetition():
    soc=DefensiveSOC(window_seconds=300,threshold=3)
    for _ in range(2):
        r=soc.ingest({"type":"auth","message":"failed login","actor":"local-user"})
        assert r["correlation"]["anomaly"] is False
    r=soc.ingest({"type":"auth","message":"failed login","actor":"local-user"})
    assert r["correlation"]["anomaly"] is True
    assert any(x["technique"]=="T1110" for x in r["attack_hints"])

def test_soc_extracts_public_ioc_and_ignores_private_ip():
    soc=DefensiveSOC()
    r=soc.ingest("connection 8.8.8.8 then 127.0.0.1 example.com")
    assert "8.8.8.8" in r["iocs"]["ipv4"]
    assert "127.0.0.1" not in r["iocs"]["ipv4"]
    assert "example.com" in r["iocs"]["domains"]

def test_soc_is_defensive_only():
    status=DefensiveSOC().status()
    assert status["active_scanning"] is False
    assert status["exploitation"] is False
