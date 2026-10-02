from __future__ import annotations
from pathlib import Path
import json
from .code_brain import CodeBrain
from .project_truth_graph import ProjectTruthGraph
from .context_compiler import ContextCompiler
from .engineering_truth import LSPTruth,DAPTruth
from .evolution_intelligence import EvolutionIntelligence
from .competence_feedback import CompetenceFeedback
from .otel_export import OTelGenAIExporter
from .kabach_agent_eval import KabachAgentEvaluation
from .architecture_policy import ArchitecturePolicy

class EngineeringIntelligence:
    """One non-authoritative facade over deterministic engineering evidence.

    Sudarshan/ProjectBrain consume this service. It does not dispatch actions,
    approve mutations, replace ProjectGraph, or become a second orchestrator.
    """
    def __init__(self,state_root):
        self.state_root=Path(state_root).resolve();self.state_root.mkdir(parents=True,exist_ok=True)
        self.code=CodeBrain();self.context=ContextCompiler();self.lsp=LSPTruth();self.dap=DAPTruth()
        self.evolution=EvolutionIntelligence();self.competence=CompetenceFeedback()
        self.otel=OTelGenAIExporter();self.kabach=KabachAgentEvaluation();self.architecture=ArchitecturePolicy()
        self._truth={}

    def truth(self,project):
        return self._truth.setdefault(str(project),ProjectTruthGraph())

    def index_project(self,project,root,persist=True):
        index=self.code.index(root)
        if persist:
            target=self.state_root/(str(project).replace("/","_").replace("\\","_")+".code-index.json")
            target.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding="utf-8")
        return index

    def compile_context(self,project,task,*,code_index,requirements=(),failures=(),max_nodes=40):
        return self.context.compile(task,code_index=code_index,truth_graph=self.truth(project),requirements=requirements,failures=failures,max_nodes=max_nodes)

    def requirement_status(self,project,requirement_id):
        return self.truth(project).requirement_status(requirement_id)

    def architecture_check(self,index,rules=()):
        return ArchitecturePolicy(rules).check(index)

    def prepare_task(self,project,root,task,*,requirements=(),failures=(),architecture_rules=(),max_nodes=40):
        index=self.index_project(project,root)
        return {"index":index,"context":self.compile_context(project,task,code_index=index,requirements=requirements,failures=failures,max_nodes=max_nodes),"architecture":self.architecture_check(index,architecture_rules),"blast_radius":self.code.blast_radius(index,task)}

    def status(self):
        return {"owner":"KRISHNA","orchestrator":"Sudarshan","authority":False,"code_brain":True,"truth_graph_projects":len(self._truth),"lsp_languages":sorted(self.lsp.SERVERS),"dap_ready":False,"external_auto_install":False}
