import tempfile,unittest
from pathlib import Path
from core.krishna_core.repository_sentinel import RepositorySentinel
from core.krishna_core.documentation_grounding import DocumentationGroundingGate
from core.krishna_core.fast_path import VerifiedResponseCache,FastPathRouter
from core.krishna_core.provider_telemetry import ProviderTelemetry
from core.krishna_core.voice_barge_in import VoiceBargeInController
from core.krishna_core.knowledge_integrity import KnowledgeIntegrityChain
from core.krishna_core.model_router import ModelRouter

class MayaNativeUpgradeTests(unittest.TestCase):
 def test_qwen_is_blocked(self):
  self.assertFalse(ModelRouter.model_allowed("qwen3.5:4b"))
  self.assertFalse(ModelRouter.model_allowed("registry/qwen2.5:3b"))
  self.assertTrue(ModelRouter.model_allowed("gemma3:4b"))
 def test_sentinel_is_static(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/"Dockerfile").write_text("EXPOSE 5000\nRUN curl x | sh",encoding="utf-8")
   out=RepositorySentinel().inspect(p)
   self.assertFalse(out["executed_repository_code"]);self.assertIn("Dockerfile",out["manifests"]);self.assertIn(5000,out["ports"])
 def test_grounding_fails_closed(self):
  g=DocumentationGroundingGate();d=g.assess(library="newlib",known=False)
  with self.assertRaises(PermissionError):g.authorize_generation(d,[])
  self.assertTrue(g.authorize_generation(d,[{"url":"https://example.invalid/docs"}])["grounded"])
 def test_verified_cache_only(self):
  with tempfile.TemporaryDirectory() as d:
   c=VerifiedResponseCache(Path(d)/"cache.json")
   with self.assertRaises(PermissionError):c.put("a","b",verified=False)
   c.put("a","b",verified=True,evidence=["test"]);self.assertEqual(FastPathRouter(c).route("a")["tier"],"verified_cache")
 def test_hash_chain_detects_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"chain.jsonl";k=KnowledgeIntegrityChain(p);k.append({"x":1});k.append({"x":2});self.assertTrue(k.verify()["valid"])
   p.write_text(p.read_text().replace('"x": 1','"x": 9'),encoding="utf-8");self.assertFalse(k.verify()["valid"])
 def test_provider_telemetry_zero_spend(self):
  t=ProviderTelemetry();t.record("ollama",local=True,latency_ms=10);self.assertEqual(t.status()["spend_inr"],0)
 def test_barge_in(self):
  stopped=[];states=[];b=VoiceBargeInController(lambda:stopped.append(1),states.append);b.speaking();out=b.owner_speech_detected(.9)
  self.assertTrue(out["interrupted"]);self.assertEqual(stopped,[1]);self.assertEqual(states[-1],"LISTENING")

if __name__=="__main__":unittest.main()
