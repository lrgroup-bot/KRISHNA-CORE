from __future__ import annotations
from pathlib import Path
from datetime import datetime,timezone
import json
from .karma_protocol import KarmaProtocol
from .brahma_council import BrahmaCouncil
from .perception_fusion import PerceptionFusion
from .model_benchmark_arena import ModelBenchmarkArena
from .reasoning_envelope import reasoning_envelope
from .agent_trace import AgentTrace
from .machine_certification import MachineCertification
from .supply_chain_gate import SupplyChainGate
from .ui_quality_gate import UIQualityGate
from .vishwakarma import VishwakarmaUpdateManager
from .project_work_policy import ProjectWorkPolicy
from .github_validation_policy import GitHubValidationPolicy

class KrishnaPowerRuntime:
 """Additive integration facade over existing KRISHNA authorities."""
 def __init__(self,state_root):
  r=Path(state_root).resolve();r.mkdir(parents=True,exist_ok=True)
  self.root=r;self.karma=KarmaProtocol(r/"karma");self.brahma=BrahmaCouncil(r/"brahma-council",self.karma)
  self.perception=PerceptionFusion();self.benchmarks=ModelBenchmarkArena()
  self.trace=AgentTrace(r/"traces"/"agents.jsonl");self.machine=MachineCertification()
  self.vishwakarma=VishwakarmaUpdateManager(r/"vishwakarma-updates")
  self.project_work=ProjectWorkPolicy();self.github_validation=GitHubValidationPolicy()
 def agent_allowed(self,agent,mutating=False):
  p=self.karma.permissions(agent)
  return p["execution_allowed"] and (not mutating or p["mutation_allowed"])
 def council(self,agents,proposals=None): return self.brahma.meeting(agents,improvement_proposals=proposals)
 def reason(self,answer,**kw): return reasoning_envelope(answer,**kw)
 def ui_gate(self,evidence): return UIQualityGate.judge(evidence)
 def release_gate(self,receipt): return SupplyChainGate.verify(receipt)
 def machine_report(self,burn_in_hours=0): return self.machine.report(burn_in_hours)
 def project_route(self,phase,**kw): return self.project_work.route(phase,**kw)
 def github_gate(self,**kw): return self.github_validation.decide(**kw)
 def status(self):
  return {"component":"KRISHNA Power Runtime","free_first":True,"paid_execution":False,
   "layers":["KARMA","BRAHMA","PERCEPTION_FUSION","MODEL_BENCHMARK_ARENA","REASONING_ENVELOPE",
             "AGENT_TRACE","UI_QUALITY_GATE","SUPPLY_CHAIN_GATE","MACHINE_CERTIFICATION","VISHWAKARMA",
             "PROJECT_WORK_POLICY","GITHUB_VALIDATION_POLICY"]}
