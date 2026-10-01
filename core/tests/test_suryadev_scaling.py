from krishna_core.suryadev_capacity import machine_snapshot,capacity_decision,recovery_policy
from krishna_core.suryadev_scheduler import slot_plan,media_speed_plan,evidence_quality_gate,source_adapter_policy

def test_fifty_is_benchmark_not_ceiling():
    d=capacity_decision(machine_snapshot(cpu_percent=30,ram_percent=35,gpu_percent=20,vram_percent=20,network_percent=10),50,max_workers=256)
    p=slot_plan(requested=50,active=50,resource_decision=d,media_requested=50,media_cap=12)
    assert p["benchmark_target"]==50 and p["not_a_ceiling"] is True
    assert p["media_slots"]==12
    assert p["lightweight_slots"]>=38

def test_overload_suspends_then_sheds():
    mid=capacity_decision(machine_snapshot(cpu_percent=86,ram_percent=70),40)
    hot=capacity_decision(machine_snapshot(cpu_percent=92,ram_percent=70),40)
    assert mid["action"]=="suspend_low_value"
    assert hot["action"]=="shed_load"
    assert recovery_policy()["per_slot_crash_isolation"] is True

def test_media_speed_adapts_to_complexity():
    easy=media_speed_plan(speech_density=.1,technical_density=.1,visual_change=.1,transcript_confidence=.95,evidence_criticality=.1)
    critical=media_speed_plan(speech_density=.8,technical_density=.9,visual_change=.8,transcript_confidence=.9,evidence_criticality=.95)
    assert easy["speed"]>critical["speed"]
    assert critical["rewind_on_low_confidence"] is True

def test_video_popularity_is_not_evidence_authority():
    good=evidence_quality_gate(authority=.9,relevance=.9,independence=.8,transcript_confidence=.9,contradiction_checked=True,timestamped=True)
    assert good["route_to_rishi"] is True
    assert "popularity" in good["rule"]
    assert source_adapter_policy()["access"].startswith("public/permitted")
