import json
import unittest


from krishna_core.hawkeye_free_cloud import HawkeyeFreeCloudFabric


class FakeOpenRouter:
    def __init__(self, fail=False):
        self.fail=fail
        self.calls=[]
    def status(self, refresh=False):
        return {"configured":True,"refresh":bool(refresh)}
    def complete(self, role, prompt, **kwargs):
        self.calls.append({"role":role,"prompt":prompt,**kwargs})
        if self.fail:
            raise RuntimeError("openrouter unavailable")
        return {"model":"vision/free","role":"vision","text":"Observed: control panel.","preflight_zero_cost":True}


class FakeDirectFree:
    def __init__(self):
        self.calls=[]
    def status(self, refresh=False):
        return {"configured":True,"automatic_zero_cost_eligible":True}
    def complete(self, prompt, **kwargs):
        self.calls.append({"prompt":prompt,**kwargs})
        return {
            "provider":"cloudflare-workers-ai","provider_id":"direct-free:cloudflare-workers-ai",
            "model":"@cf/free","text":"Reviewer: evidence is plausible.","zero_cost_verified":True,
        }


class FakeGemini:
    def __init__(self):
        self.calls=[]
    def status(self):
        return {"configured":True,"provider":"google-gemini","free_only_declared":True}
    def analyze_image(self,data,content_type,prompt,metadata=None):
        self.calls.append((data,content_type,prompt,metadata))
        return {"model":"gemini-free","analysis":"Observed: machine housing."}


class FakeGateway:
    def __init__(self):
        self.completions=[]
    def list(self):
        return {"profiles":[
            {"id":"groq1","name":"Groq Free","base_url":"https://api.groq.com/openai/v1",
             "model":"free-groq-model","free_only":True,"enabled":True,
             "credential_available":True,"created_at":2},
            {"id":"paid1","name":"Paid","base_url":"https://example.com/v1",
             "model":"paid-model","free_only":False,"enabled":True,
             "credential_available":True,"created_at":1},
        ]}
    def complete(self,profile_id,prompt,system="",max_tokens=0):
        self.completions.append((profile_id,prompt,system,max_tokens))
        return "Independent review."


class HawkeyeFreeCloudFabricTests(unittest.TestCase):
    def make(self, openrouter=None):
        self.openrouter=openrouter or FakeOpenRouter()
        self.direct=FakeDirectFree()
        self.gateway=FakeGateway()
        self.gemini=FakeGemini()
        return HawkeyeFreeCloudFabric(self.openrouter,self.direct,self.gateway,self.gemini)

    def meta(self, **extra):
        row={"cloud_approved":True,"selected_keyframe":True}
        row.update(extra)
        return row

    def test_status_declares_no_mobile_qwen_and_no_paid_fallback(self):
        out=self.make().status()
        self.assertFalse(out["mobile_qwen"])
        self.assertFalse(out["billing"]["paid_fallback"])
        ids=[x["id"] for x in out["providers"]["declared_free_text_gateways"]]
        self.assertEqual(ids,["groq1"])

    def test_sensitive_keyframe_is_blocked_before_any_cloud_call(self):
        fabric=self.make()
        with self.assertRaises(PermissionError):
            fabric.analyze_image(
                b"jpeg","image/jpeg","inspect",
                self.meta(contains_biometrics=True),
            )
        self.assertEqual(self.openrouter.calls,[])
        self.assertEqual(self.gemini.calls,[])
        self.assertEqual(self.direct.calls,[])
        self.assertEqual(self.gateway.completions,[])

    def test_auto_prefers_openrouter_role_and_uses_text_only_reviews(self):
        fabric=self.make()
        out=fabric.analyze_image(
            b"jpeg","image/jpeg","inspect machine",
            self.meta(),provider="auto",openrouter_role="hawkeye_vision",
            preferred_model="vision/free",include_reviews=True,
        )
        self.assertEqual(out["provider"],"openrouter")
        self.assertEqual(out["model"],"vision/free")
        call=self.openrouter.calls[0]
        self.assertEqual(call["role"],"hawkeye_vision")
        self.assertEqual(call["preferred_model"],"vision/free")
        self.assertTrue(str(call["image_data_url"]).startswith("data:image/jpeg;base64,"))
        self.assertTrue(self.direct.calls)
        self.assertEqual(self.gateway.completions[0][0],"groq1")
        self.assertNotIn("data:image",self.gateway.completions[0][1])
        self.assertGreaterEqual(len(out["reviews"]),2)

    def test_auto_falls_back_to_gemini_when_openrouter_fails(self):
        fabric=self.make(FakeOpenRouter(fail=True))
        out=fabric.analyze_image(
            b"jpeg","image/jpeg","inspect",self.meta(),
            provider="auto",include_reviews=False,
        )
        self.assertEqual(out["provider"],"google-gemini")
        self.assertEqual(out["reviews"],[])
        self.assertTrue(out["attempts"])
        self.assertEqual(len(self.gemini.calls),1)

    def test_recorded_pc_finding_skips_duplicate_local_vision(self):
        row=HawkeyeFreeCloudFabric.recorded_pc_finding({
            "free_cloud":{
                "analysis":"Observed pump housing.",
                "provider":"openrouter",
                "model":"vision/free",
                "role":"hawkeye_vision",
                "pc_recorded":True,
                "pc_observation_id":"obs-1",
                "pc_session_id":"pc-1",
            }
        })
        self.assertIsNotNone(row)
        self.assertEqual(row["pc_observation_id"],"obs-1")
        self.assertEqual(row["provider"],"openrouter")

    def test_force_pc_vision_overrides_recorded_cloud_finding(self):
        row=HawkeyeFreeCloudFabric.recorded_pc_finding({
            "force_pc_vision":True,
            "free_cloud":{
                "analysis":"Observed pump housing.",
                "pc_recorded":True,
                "pc_observation_id":"obs-1",
            }
        })
        self.assertIsNone(row)

    def test_provider_pin_does_not_cross_to_other_vision_provider(self):
        fabric=self.make(FakeOpenRouter(fail=True))
        with self.assertRaises(RuntimeError):
            fabric.analyze_image(
                b"jpeg","image/jpeg","inspect",self.meta(),
                provider="openrouter",include_reviews=False,
            )
        self.assertEqual(self.gemini.calls,[])


if __name__=="__main__":
    unittest.main()
