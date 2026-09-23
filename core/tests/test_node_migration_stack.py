import tempfile,unittest
from pathlib import Path
from krishna_core.node_registry import NodeRegistry
from krishna_core.knowledge_sync import KnowledgeSync
from krishna_core.node_transfer import resume_copy
from krishna_core.node_installer import NodeInstaller,HardwareProfile
class T(unittest.TestCase):
 def test_registry_requires_approval(self):
  with tempfile.TemporaryDirectory() as d:
   r=NodeRegistry(Path(d)/"nodes.json")
   with self.assertRaises(PermissionError): r.enroll("laptop","fp")
   self.assertTrue(r.enroll("laptop","fp",approved=True).trusted)
 def test_knowledge_merge(self):
  with tempfile.TemporaryDirectory() as d:
   a,b=Path(d)/"a",Path(d)/"b"; a.write_text('{"id":"1","v":"x"}\n',encoding="utf-8")
   self.assertEqual(KnowledgeSync().merge_jsonl(a,b)["added"],1)
 def test_resume_transfer(self):
  with tempfile.TemporaryDirectory() as d:
   a,b=Path(d)/"a",Path(d)/"b"; a.write_bytes(b"abcdef"); b.write_bytes(b"abc"); self.assertEqual(resume_copy(a,b)["bytes"],6)
 def test_installer_acceptance(self):
  i=NodeInstaller(); self.assertEqual(i.plan(True,HardwareProfile("x",16,"g"))["state"],"READY"); self.assertEqual(i.accept({"core":True,"guardian":True})["state"],"READY")
