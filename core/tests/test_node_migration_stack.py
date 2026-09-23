import tempfile,unittest
from pathlib import Path
from krishna_core.node_registry import NodeRegistry
from krishna_core.knowledge_sync import KnowledgeSync
from krishna_core.node_transfer import resume_copy
from krishna_core.node_installer import NodeInstaller,HardwareProfile

class T(unittest.TestCase):
 def test_registry_requires_approval_and_strong_identity(self):
  with tempfile.TemporaryDirectory() as d:
   r=NodeRegistry(Path(d)/"nodes.json")
   with self.assertRaises(PermissionError): r.enroll("laptop","0123456789abcdef")
   with self.assertRaises(ValueError): r.enroll("laptop","fp",approved=True)
   node=r.enroll("laptop","0123456789abcdef",approved=True)
   self.assertTrue(node.trusted)
   with self.assertRaises(ValueError):r.enroll("duplicate","0123456789abcdef",approved=True)
 def test_knowledge_merge_reports_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   a,b=Path(d)/"a",Path(d)/"b"
   a.write_text('{"id":"1","v":"new"}\n{"id":"2","v":"x"}\n',encoding="utf-8")
   b.write_text('{"id":"1","v":"old"}\n',encoding="utf-8")
   out=KnowledgeSync().merge_jsonl(a,b)
   self.assertEqual(out["added"],1);self.assertEqual(out["conflict_count"],1)
   rows=KnowledgeSync().read_jsonl(b)
   self.assertEqual(next(x for x in rows if x["id"]=="1")["v"],"old")
 def test_resume_transfer_recovers_corrupt_partial(self):
  with tempfile.TemporaryDirectory() as d:
   a,b=Path(d)/"a",Path(d)/"b"
   a.write_bytes(b"abcdef"); b.write_bytes(b"zzz")
   out=resume_copy(a,b)
   self.assertEqual(out["bytes"],6);self.assertEqual(b.read_bytes(),b"abcdef")
 def test_installer_acceptance(self):
  i=NodeInstaller(); self.assertEqual(i.plan(True,HardwareProfile("x",16,"g"))["state"],"READY"); self.assertEqual(i.accept({"core":True,"guardian":True})["state"],"READY")
