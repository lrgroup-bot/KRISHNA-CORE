import tempfile
import unittest
from pathlib import Path

from krishna_core.memory import MemoryStore
from krishna_core.gyan_bhandar import GyanBhandarAgent

class NoopGaruda:
    def scout(self,*args,**kwargs):
        return {"web":[],"github":[]}

class GyanMemoryFabricTests(unittest.TestCase):
    def test_typed_inventory_and_supersession(self):
        with tempfile.TemporaryDirectory() as td:
            mem=MemoryStore(Path(td)/"memory.db")
            g=GyanBhandarAgent(mem,NoopGaruda())
            first=g.store("KRISHNA","router","Use local-first routing",[],0.7,"test",True,"semantic",{"doc":"a"})
            inv=g.inventory("KRISHNA")
            self.assertEqual(inv["kinds"]["semantic"]["verified"],1)
            proposal=g.supersede("KRISHNA",first["fingerprint"],"router","Use privacy-aware local-first routing",[],0.9,"test",True,"semantic",{"doc":"b"})
            self.assertTrue(proposal["requires_user_approval"])
            decided=g.decide(proposal["approval_id"],True)
            self.assertTrue(decided["stored"])
            rows=g.recall("KRISHNA","router",100,False,None,True)
            old=next(x for x in rows if x["fingerprint"]==first["fingerprint"])
            self.assertEqual(old["status"],"superseded")
            self.assertTrue(old["superseded_by"])
            current=g.recall("KRISHNA","router",100,True)
            self.assertEqual(len(current),1)
            self.assertIn("privacy-aware",current[0]["lesson"])
            inv=g.inventory("KRISHNA")
            self.assertEqual(inv["kinds"]["semantic"]["superseded"],1)
            mem.close()

    def test_pending_keeps_type_provenance_and_supersedes(self):
        with tempfile.TemporaryDirectory() as td:
            mem=MemoryStore(Path(td)/"memory.db")
            g=GyanBhandarAgent(mem,NoopGaruda())
            p=g.propose("KRISHNA","skill:x","Verified workflow",[],0.8,"test",False,"skill",{"source":"unit"},"oldfp")
            row=g.pending("KRISHNA")[0]
            self.assertEqual(row["memory_kind"],"skill")
            self.assertEqual(row["provenance"]["source"],"unit")
            self.assertEqual(row["supersedes"],"oldfp")
            mem.close()

    def test_invalid_memory_kind_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            mem=MemoryStore(Path(td)/"memory.db")
            with self.assertRaises(ValueError):
                mem.learn("KRISHNA","x","y",memory_kind="anything")
            mem.close()

if __name__=="__main__": unittest.main()
