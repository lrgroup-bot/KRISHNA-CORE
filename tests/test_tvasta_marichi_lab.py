import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1] / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from krishna_core.rishi_council import RishiCouncil
from krishna_core.lab_bot import LabBot

def test_tvasta_and_marichi_are_permanent_specialists(tmp_path):
    council = RishiCouncil()
    tvasta = council.get("tvasta")
    marichi = council.get("marichi")
    assert "biological computing" in tvasta["domains"]
    assert "computer architecture" in tvasta["domains"]
    assert "rocket science" in marichi["domains"]
    assert "reusable launch vehicles" in marichi["domains"]

def test_lab_research_proposal_captures_discovery_fields(tmp_path):
    lab = LabBot(tmp_path)
    row = lab.request({
        "rishi": "tvasta",
        "domain": "computing",
        "mode": "simulation",
        "hypothesis": "A new computing substrate may improve a defined workload.",
        "objective": "Compare the proposed substrate with a conventional baseline.",
        "controls": ["conventional baseline"],
        "measurements": ["accuracy", "energy estimate"],
        "success_criteria": ["predefined improvement without loss of validity"],
        "novelty": "cross-domain computing substrate",
        "prior_work": ["paper:example"],
        "collaborating_rishis": ["gautama", "bharadvaja"],
        "failure_criteria": ["cannot reproduce claimed advantage"],
        "contradictory_evidence": ["record negative and conflicting studies"],
        "ip_patent_refs": ["patent-search-required"],
        "possible_applications": ["low-energy adaptive computing"],
        "what_else_can_this_become": ["new sensing-compute interface"],
        "technology_maturity": "research prototype",
    })
    p = row["proposal"]
    assert p["technology_maturity"] == "research prototype"
    assert p["collaborating_rishis"] == ["gautama", "bharadvaja"]
    assert p["what_else_can_this_become"]

def test_deep_subject_ontology_has_cross_domain_depth():
    from krishna_core.subject_ontology import SUBJECT_DEPTH, FRONTIER_AXES, find_subject, gap_report
    assert "computing_digital_systems" in SUBJECT_DEPTH
    assert "life_health_sciences" in SUBJECT_DEPTH
    assert "aerospace_space" in SUBJECT_DEPTH
    assert "earth_environment_agriculture" in SUBJECT_DEPTH
    assert "what_else_can_this_become" in FRONTIER_AXES
    assert any(x["specialty"] == "organoid intelligence" for x in find_subject("organoid intelligence computer"))
    council_ids = [x["id"] for x in RishiCouncil().list()]
    assert gap_report(council_ids) == []

def test_new_rishi_proposals_require_brahma_krishna_truth_debate(tmp_path):
    from krishna_core.brahmagyan import BrahmagyanRuntime
    bg = BrahmagyanRuntime(tmp_path, None, type("M",(),{"audit":lambda *a,**k:None})())
    p = bg.propose_council_specialist("new frontier", "New Frontier Scholar", "No existing owner covers it deeply.")
    assert p["decision_status"] == "awaiting_brahma_krishna_truth_debate"
    assert p["governance"]["brahma_review_required"]
    assert p["governance"]["krishna_review_required"]
    assert p["governance"]["truth_debate_required"]
    assert p["governance"]["gautama_evidence_review_required"]
    assert p["governance"]["shishya_first_required"]

def test_shishya_scaling_is_not_fixed_to_eight(tmp_path, monkeypatch):
    from krishna_core.brahmagyan import Brahmagyan
    monkeypatch.setenv("KRISHNA_SHISHYA_MAX_CONCURRENT", "24")
    bg = Brahmagyan(tmp_path)
    m = bg.create_mission("KRISHNA", "deep computing research", "Map independent specialties")
    plan = bg.shishya_plan(m["mission_id"], count=40)
    assert plan["max_concurrent"] == 24
    assert plan["requested_count"] == 40
    assert plan["scale_governance"]["fixed_eight_limit"] is False
    assert plan["scale_governance"]["brahma_review_required"]
    assert plan["scale_governance"]["ai_hr_review_required"]

def test_research_team_governor_expands_and_stops_on_information_gain():
    from krishna_core.research_team_governor import research_team_decision
    grow = research_team_decision(current=12, uncovered_specialties=7, contradictions=3)
    assert grow["action"] == "expand" and grow["delta"] == 10
    stop = research_team_decision(current=22, duplicate_ratio=.8, information_gain=.1)
    assert stop["action"] == "stop_expansion"

def test_deep_research_deadline_is_sixty_seconds():
    from krishna_core.research_deadline import deadline_plan, evidence_lane_priority
    p=deadline_plan("deep question")
    assert p["budget_seconds"] == 60
    assert "contradictions" in p["parallel_lanes"]
    assert p["slow_evidence_policy"].startswith("return unresolved")
    fast=evidence_lane_priority(authority=1,relevance=1,freshness=1,independence=1,information_gain=1,latency_seconds=2)
    slow=evidence_lane_priority(authority=1,relevance=1,freshness=1,independence=1,information_gain=1,latency_seconds=20)
    assert fast > slow

def test_live_topics_can_be_prewarmed_without_krishna_load():
    from krishna_core.live_knowledge import prewarm_plan
    p=prewarm_plan(["AI accelerators","rocket propulsion"])
    assert p["krishna_load"] is False
    assert "contradiction_index" in p["topics"][0]["prepare"]

def test_brahmagyan_collectors_stream_and_redirect():
    from krishna_core.brahmagyan_collectors import collector_team_plan, collection_decision
    p=collector_team_plan(["tvasta","marichi","gautama"],contradictions=2,unresolved=1)
    assert p["streaming_collection"] is True
    assert "research_conductor" in p["roles"]
    d=collection_decision(supported_sources=3,independent_sources=2)
    assert d["action"] == "synthesize"

def test_api_first_acquisition_and_capacity():
    from krishna_core.knowledge_acquisition import acquisition_route, device_capacity_plan
    assert acquisition_route(api_available=True)["mode"] == "public_api"
    assert acquisition_route(visual_required=True)["worker"] == "CHANDRADEV"
    p=device_capacity_plan(queued_io_jobs=8,queued_visual_jobs=2)
    assert p["requested_nodes"] == 4
    assert p["purchase_required"] is False

def test_research_fellowship_requires_evidence_and_examination():
    from krishna_core.research_fellowship import new_fellow,promotion_review,permanence_review
    f=new_fellow("marichi","rocket propulsion","Agnivega")
    good={k:.9 for k in ("evidence_quality","replication","reasoning","correction_behavior","safety_reliability","collaboration","resource_efficiency")}
    r=promotion_review(f,"intern_shishya",good)
    assert r["approved"] is True
    p=permanence_review(workload_ratio=.9,specialty_depth=.9,knowledge_continuity=.9,validated_output=.9,duplicate_ratio=.1,resource_value=.9)
    assert p["recommended"] is True and p["probation_required"] is True

def test_engineering_program_never_optimizes_cost_alone():
    from krishna_core.research_programs import ROCKET_PROGRAM
    assert "safety" in ROCKET_PROGRAM["optimization"]["maximize"]
    assert "manufacturing_cost" in ROCKET_PROGRAM["optimization"]["minimize"]
    assert ROCKET_PROGRAM["optimization"]["selection"].startswith("pareto_frontier")
    assert "separately" in ROCKET_PROGRAM["readiness_policy"]

def test_suryadev_capacity_governor_expands_and_protects_node():
    from krishna_core.suryadev_capacity import machine_snapshot,capacity_decision,browser_policy,recovery_policy
    low=machine_snapshot(cpu_percent=35,ram_percent=40,gpu_percent=20,vram_percent=20,network_percent=10)
    assert capacity_decision(low,10)["target_workers"] > 10
    high=machine_snapshot(cpu_percent=92,ram_percent=75,gpu_percent=60,vram_percent=50,network_percent=30)
    assert capacity_decision(high,20)["action"] == "shed_load"
    assert capacity_decision(high,20)["target_workers"] < 20
    assert browser_policy()["branded_chrome_required"] is False
    assert recovery_policy()["resume_from_checkpoint"] is True
