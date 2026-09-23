import unittest
from krishna_core.model_scout import ZeroCostPolicy
from krishna_core.unified_model_mesh import UnifiedModelMesh, Worker
from krishna_core.cloud_providers import QuotaExhausted

class Fake:
    def __init__(self,text="ok",error=None): self.text=text; self.error=error
    def complete(self,req):
        if self.error: raise self.error
        return {"text":self.text,"headers":{}}

class UnifiedMeshTests(unittest.TestCase):
    def test_private_never_routes_cloud(self):
        m=UnifiedModelMesh();m.add(Worker("cloud",Fake(),"m",confirmed_free=True))
        m.add(Worker("local",Fake("local"),"m",local=True))
        self.assertEqual(m.dispatch("x",privacy="local_only")["provider"],"local")
    def test_paid_or_unconfirmed_cloud_is_never_eligible(self):
        m=UnifiedModelMesh();m.add(Worker("unknown",Fake(),"m",confirmed_free=False))
        with self.assertRaises(RuntimeError):m.dispatch("x")
    def test_exhausted_provider_is_suspended_and_zero_cost_fallback_used(self):
        m=UnifiedModelMesh()
        m.add(Worker("a",Fake(error=QuotaExhausted("limit")),"m",confirmed_free=True,priority=10))
        m.add(Worker("b",Fake("free-b"),"m",confirmed_free=True,priority=5))
        r=m.dispatch("x")
        self.assertEqual(r["provider"],"b");self.assertEqual(r["cost_usd"],0.0)
        self.assertFalse(m.zero_cost.cloud_allowed("a",confirmed_free=True))
    def test_load_changes_selection(self):
        m=UnifiedModelMesh()
        a=Worker("a",Fake("a"),"m",confirmed_free=True,priority=5,inflight=10)
        b=Worker("b",Fake("b"),"m",confirmed_free=True,priority=4)
        m.add(a);m.add(b);self.assertEqual(m.dispatch("x")["provider"],"b")

if __name__=="__main__":unittest.main()
