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
    from krishna_core.brahmagyan import Brahmagyan
    bg = Brahmagyan(tmp_path)
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
