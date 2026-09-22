from krishna_core.autonomy_harness import AutonomyHarness,HarnessState
from krishna_core.threat_intel import ThreatIntel
from krishna_core.ops_monitor import OpsMonitor

def test_harness_requires_checker_success():
    h=AutonomyHarness(max_attempts=2)
    s=HarnessState("fix project")
    first=h.evaluate(s,[{"name":"tests","ok":False}])
    assert first["phase"]=="repairing"
    second=h.evaluate(s,[{"name":"tests","ok":True},{"name":"runtime","ok":True}])
    assert second["phase"]=="verified"

def test_threat_intel_never_autoblocks():
    t=ThreatIntel(); t.add_ip("8.8.8.8","test",0.9)
    d=t.decision("8.8.8.8")
    assert d["known"] is True and d["auto_block"] is False and d["requires_policy_gate"] is True

def test_ops_monitor_dns_shape():
    r=OpsMonitor().dns("localhost")
    assert "ok" in r and "addresses" in r
