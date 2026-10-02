from pathlib import Path
from krishna_core.code_brain import CodeBrain
from krishna_core.project_truth_graph import ProjectTruthGraph
from krishna_core.context_compiler import ContextCompiler
from krishna_core.engineering_truth import LSPTruth,DAPTruth
from krishna_core.mission_replay import MissionReplayLedger
from krishna_core.evolution_intelligence import EvolutionIntelligence
from krishna_core.competence_feedback import CompetenceFeedback
from krishna_core.otel_export import OTelGenAIExporter
from krishna_core.kabach_agent_eval import KabachAgentEvaluation

def test_code_brain_indexes_python_and_blast_radius(tmp_path):
    (tmp_path/"a.py").write_text("import b\ndef login(x): return x\n",encoding="utf-8")
    (tmp_path/"test_a.py").write_text("def test_login(): pass\n",encoding="utf-8")
    idx=CodeBrain().index(tmp_path)
    assert any(x["name"]=="login" for x in idx["nodes"])
    assert "test_a.py" in idx["test_files"]
    assert CodeBrain().blast_radius(idx,"login")["count"]>=1

def test_truth_graph_requires_code_test_runtime_evidence():
    g=ProjectTruthGraph()
    for i,k in [("AUTH-001","requirement"),("auth.py","code"),("test-auth","test"),("run-1","runtime_evidence")]:g.add(i,k)
    g.link("AUTH-001","auth.py","implemented_by");g.link("auth.py","test-auth","verified_by");g.link("test-auth","run-1","runtime_verified_by")
    assert g.requirement_status("AUTH-001")["complete"] is True

def test_context_compiler_is_bounded(tmp_path):
    (tmp_path/"auth.py").write_text("def login(): pass\n",encoding="utf-8")
    idx=CodeBrain().index(tmp_path)
    out=ContextCompiler().compile("fix login",code_index=idx,max_nodes=1)
    assert len(out["code"])<=1 and out["index_digest"]==idx["digest"]

def test_lsp_and_dap_fail_closed(tmp_path):
    assert LSPTruth().plan("not-a-language")["available"] is False
    assert DAPTruth().plan("python",tmp_path)["ready"] is False

def test_mission_replay_resume(tmp_path):
    l=MissionReplayLedger(tmp_path/"replay.db");l.record("m1","s1",inputs={"a":1},result={"ok":1});l.record("m1","s2",state="failed")
    assert l.resume_point("m1")["last_verified_step"]=="s1"

def test_evolution_and_test_gap_contract(tmp_path):
    (tmp_path/"a.py").write_text("def a(): pass\n",encoding="utf-8");b=CodeBrain().index(tmp_path)
    (tmp_path/"a.py").write_text("def a(): pass\ndef b(): pass\n",encoding="utf-8");a=CodeBrain().index(tmp_path)
    assert EvolutionIntelligence().compare(b,a)["symbols_added"]
    assert EvolutionIntelligence().test_gaps(a,["a.py"])["heuristic"] is True

def test_competence_feedback_finds_repeated_weakness():
    rows=[{"agent":"repair","domain":"flutter","passed":False} for _ in range(3)]
    assert CompetenceFeedback().weaknesses(rows)

def test_otel_mapping_does_not_export_prompt_content():
    s=OTelGenAIExporter().span({"agent":"worker","project":"p","mission":"m","verified":True,"prompt":"secret"})
    assert "prompt" not in str(s)

def test_kabach_eval_is_isolated_and_authorized():
    p=KabachAgentEvaluation().plan("candidate")
    assert p["production"] is False and p["requires_authorization"] is True

from krishna_core.engineering_intelligence import EngineeringIntelligence

def test_engineering_intelligence_is_single_non_authoritative_facade(tmp_path):
    (tmp_path/"src.py").write_text("def build(): return True\n",encoding="utf-8")
    svc=EngineeringIntelligence(tmp_path/"state")
    idx=svc.index_project("demo",tmp_path)
    ctx=svc.compile_context("demo","build",code_index=idx)
    assert ctx["code"]
    status=svc.status()
    assert status["owner"]=="KRISHNA"
    assert status["orchestrator"]=="Sudarshan"
    assert status["authority"] is False
    assert status["external_auto_install"] is False

from krishna_core.architecture_policy import ArchitecturePolicy
from krishna_core.sudarshan_project_orchestrator import SudarshanProjectOrchestrator

def test_architecture_policy_blocks_forbidden_dependency():
    idx={"edges":[{"source":"ui/login.py","target":"database","kind":"imports"}]}
    result=ArchitecturePolicy([{"id":"ARCH-1","source":"^ui/","target":"database","allowed":False}]).check(idx)
    assert result["passed"] is False and result["violations"][0]["rule"]=="ARCH-1"

def test_sudarshan_prepares_engineering_context_and_blocks_architecture(tmp_path):
    (tmp_path/"ui.py").write_text("import database\ndef login(): pass\n",encoding="utf-8")
    svc=EngineeringIntelligence(tmp_path/"state")
    s=SudarshanProjectOrchestrator(engineering_intelligence=svc)
    ready=s.prepare_engineering_task("demo",tmp_path,"login")
    assert ready["state"]=="READY_ENGINEERING_CONTEXT"
    blocked=s.prepare_engineering_task("demo",tmp_path,"login",architecture_rules=[{"id":"NO-DB","source":"^ui.py$","target":"database","allowed":False}])
    assert blocked["state"]=="BLOCKED_ARCHITECTURE_POLICY"
