import unittest

from krishna_core.memory_fabric import MemoryFabric


class FakeMemory:
    def remember(self,*args,**kwargs):
        return None


class FakeGyan:
    def recall(self,*args,**kwargs):
        return []
    def inventory(self,*args,**kwargs):
        return {}
    def store(self,*args,**kwargs):
        return {"stored":True}


class FakeCBM:
    def status(self):
        return {"available":True}
    def query(self,text,project_root=None,limit=20):
        return {"query":text,"root":str(project_root),"limit":limit}


class FakeGraft:
    def status(self):
        return {"available":True}
    def query(self,text):
        return "graft:"+text


class OptionalMemoryAdapterTests(unittest.TestCase):
    def test_codebase_memory_is_read_only_context(self):
        fabric=MemoryFabric(FakeMemory(),FakeGyan(),codebase_memory=FakeCBM())
        out=fabric.structural_context("/tmp/project","find controller",limit=7)
        self.assertTrue(out["available"])
        self.assertIn("read-only",out["authority"])
        self.assertEqual(out["results"]["limit"],7)

    def test_graft_never_replaces_gyan_authority(self):
        fabric=MemoryFabric(FakeMemory(),FakeGyan(),graft=FakeGraft())
        out=fabric.optional_memory_query("topic")
        self.assertTrue(out["available"])
        self.assertIn("Gyan-Bhandar",out["authority"])

    def test_missing_optional_adapters_fail_honestly(self):
        fabric=MemoryFabric(FakeMemory(),FakeGyan())
        self.assertFalse(fabric.structural_context("/tmp","x")["available"])
        self.assertFalse(fabric.optional_memory_query("x")["available"])


if __name__=="__main__":
    unittest.main()
