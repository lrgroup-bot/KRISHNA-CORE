import unittest

from krishna_core.router import ModelRouter


class FakeControlPlane:
    def __init__(self):
        self.calls=[]
    def action(self,action,payload,**kwargs):
        self.calls.append((action,dict(payload),dict(kwargs)))
        return {
            "action_id":"a1","status":"completed","verified":True,
            "result":{"provider":payload["provider"],"model":"fake","text":"governed"},
        }


class GovernedRouterTests(unittest.TestCase):
    def test_route_uses_sudarshan_when_bound(self):
        router=ModelRouter()
        gate=FakeControlPlane()
        router.bind_sudarshan(gate)
        out=router.route("hello",privacy="local_only",project="KUBER",actor="conversation")
        self.assertEqual(out,{"provider":"ollama","text":"governed"})
        self.assertEqual(len(gate.calls),1)
        action,payload,kwargs=gate.calls[0]
        self.assertEqual(action,"model.complete")
        self.assertEqual(payload["privacy"],"local_only")
        self.assertEqual(kwargs["project"],"KUBER")
        self.assertEqual(kwargs["actor"],"conversation")
        self.assertEqual(kwargs["source"],"system")

    def test_route_does_not_call_direct_ask_when_sudarshan_bound(self):
        router=ModelRouter()
        gate=FakeControlPlane()
        router.bind_sudarshan(gate)
        router.ask=lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("direct ask bypass"))
        out=router.route("hello",privacy="local_only",project="KRISHNA")
        self.assertEqual(out["text"],"governed")


if __name__=="__main__":
    unittest.main()
