import tempfile,unittest
from pathlib import Path
from krishna_core.perception_fusion import PerceptionFusion
from krishna_core.model_benchmark_arena import ModelBenchmarkArena
from krishna_core.reasoning_envelope import reasoning_envelope
from krishna_core.agent_trace import AgentTrace
from krishna_core.machine_certification import MachineCertification
from krishna_core.supply_chain_gate import SupplyChainGate
from krishna_core.ui_quality_gate import UIQualityGate
class PowerUpTests(unittest.TestCase):
 def test_perception_prefers_structure_and_verifies(self):
  p=PerceptionFusion();p.observe("screen","vlm",{"x":1},.9);p.observe("uia","ui_tree",{"button":"Save"},.8)
  self.assertEqual(p.scene()["best"]["kind"],"ui_tree");self.assertTrue(p.verify_change({"a":1},{"a":2})["verified"])
 def test_benchmark_free_private(self):
  a=ModelBenchmarkArena();a.record(provider="local",model="m",task="code",quality=.8,latency_ms=10)
  self.assertEqual(a.choose("code",private=True)["provider"],"local")
  with self.assertRaises(ValueError):a.record(provider="x",model="p",task="code",quality=1,latency_ms=1,money_cost=1)
 def test_reasoning_uncertainty(self): self.assertTrue(reasoning_envelope("x",confidence=.5)["verification_required"])
 def test_trace(self):
  with tempfile.TemporaryDirectory() as d:
   t=AgentTrace(Path(d)/"t.jsonl")
   with t.span("work"):pass
   self.assertEqual(len((Path(d)/"t.jsonl").read_text().splitlines()),2)
 def test_machine_requires_real_evidence(self):
  m=MachineCertification();self.assertFalse(m.report(24)["certified"])
 def test_supply_chain(self):
  self.assertFalse(SupplyChainGate.verify({"source_commit":"x"})["passed"])
 def test_ui_gate(self):
  e={x:True for x in UIQualityGate.REQUIRED};self.assertTrue(UIQualityGate.judge(e)["package_allowed"])
if __name__=="__main__":unittest.main()
