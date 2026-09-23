import base64
import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.openrouter_free import OpenRouterFreeFabric, ZeroCostPolicyError


class FakeGateway:
    def __init__(self, models=None, image_cost="0"):
        self.calls=[]
        self.models=models or [
            {
                "id":"moonshotai/kimi-k2.6:free","name":"Kimi K2.6 Free",
                "context_length":262144,
                "architecture":{"input_modalities":["text","image"],"output_modalities":["text"]},
                "pricing":{"prompt":"0","completion":"0"},
                "supported_parameters":["tools","structured_outputs"],
                "expiration_date":None,
            },
            {
                "id":"inclusionai/ling-3.0-flash-vl:free","name":"Ling 3.0 Flash VL",
                "context_length":262144,
                "architecture":{"input_modalities":["text","image","video"],"output_modalities":["text"]},
                "pricing":{"prompt":"0","completion":"0","image":"0"},
                "supported_parameters":["tools"],
                "expiration_date":None,
            },
            {
                "id":"inclusionai/ling-3.0-flash-sante:free","name":"Ling 3.0 Flash Sante",
                "context_length":262144,
                "architecture":{"input_modalities":["text"],"output_modalities":["text"]},
                "pricing":{"prompt":"0","completion":"0"},
                "supported_parameters":["tools"],
                "expiration_date":None,
            },
            {
                "id":"inclusionai/ming-image-0.1-design","name":"Ming Image 0.1 Design",
                "architecture":{"input_modalities":["text"],"output_modalities":["image"]},
                "pricing":{"prompt":image_cost,"completion":"0","image":"0"},
                "supported_parameters":[],
                "expiration_date":None,
            },
            {
                "id":"paid/model","name":"Paid",
                "architecture":{"input_modalities":["text"],"output_modalities":["text"]},
                "pricing":{"prompt":"0.000001","completion":"0"},
            },
        ]

    def list(self):
        return {"profiles":[{
            "id":"or1","name":"OpenRouter-Free","base_url":"https://openrouter.ai/api/v1",
            "model":"openrouter/free","free_only":True,"enabled":True,
            "credential_backend":"windows-dpapi","credential_available":True,"created_at":10,
        }]}

    def request_json(self, profile_id, path, payload=None, method=None, timeout=120):
        self.calls.append({"profile_id":profile_id,"path":path,"payload":payload,"method":method})
        if path=="/models":
            return {"data":self.models}
        if path=="/images/models":
            return {"data":[{
                "id":"inclusionai/ming-image-0.1-design",
                "supported_parameters":{
                    "output_format":{"type":"enum","values":["png","jpeg","webp"]},
                    "n":{"type":"range","min":1,"max":1},
                    "input_references":{"type":"range","min":0,"max":0},
                },
            }]}
        if path=="/chat/completions":
            return {"choices":[{"message":{"content":"ok"}}],"usage":{"cost":0}}
        if path=="/images":
            return {"data":[{"b64_json":base64.b64encode(b"fake-png").decode()}],"usage":{"cost":0}}
        raise AssertionError(path)


class OpenRouterFreeFabricTests(unittest.TestCase):
    def test_role_ranking_filters_paid_models_and_selects_specialists(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=OpenRouterFreeFabric(FakeGateway(),td)
            self.assertIn("kimi",fabric.rank("coding",1,refresh=True)[0]["id"])
            self.assertIn("ling-3.0-flash-vl",fabric.rank("vision",1)[0]["id"])
            self.assertIn("sante",fabric.rank("medical",1)[0]["id"])
            all_ids={x["id"] for x in fabric.rank("general",20)}
            self.assertNotIn("paid/model",all_ids)

    def test_cloud_privacy_and_secret_guards_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=OpenRouterFreeFabric(FakeGateway(),td)
            with self.assertRaises(PermissionError):
                fabric.complete("general","hello",privacy="local_only")
            with self.assertRaises(PermissionError):
                fabric.complete("general","api_key=super-secret-value",privacy="approved_cloud")
            with self.assertRaises(PermissionError):
                fabric.complete("general","hello",privacy="approved_cloud",sensitive=True)

    def test_completion_refreshes_zero_cost_catalog_and_disables_provider_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            gateway=FakeGateway()
            fabric=OpenRouterFreeFabric(gateway,td)
            result=fabric.complete("coding","write a bounded test",privacy="approved_cloud")
            self.assertEqual(result["text"],"ok")
            self.assertTrue(result["preflight_zero_cost"])
            chat=next(x for x in gateway.calls if x["path"]=="/chat/completions")
            self.assertEqual(chat["payload"]["provider"]["allow_fallbacks"],False)
            self.assertEqual(chat["payload"]["provider"]["data_collection"],"deny")
            self.assertTrue(chat["payload"]["provider"]["zdr"])
            self.assertTrue(any(x["path"]=="/models" for x in gateway.calls))

    def test_vision_accepts_only_local_data_image_urls(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=OpenRouterFreeFabric(FakeGateway(),td)
            with self.assertRaises(ValueError):
                fabric.complete("vision","inspect",privacy="approved_cloud",image_data_url="https://example.com/a.png")
            result=fabric.complete("vision","inspect",privacy="approved_cloud",image_data_url="data:image/png;base64,AA==")
            self.assertEqual(result["text"],"ok")

    def test_zero_cost_ming_image_is_saved_without_dimension_controls(self):
        with tempfile.TemporaryDirectory() as td:
            gateway=FakeGateway()
            fabric=OpenRouterFreeFabric(gateway,td)
            result=fabric.generate_image("clean dashboard poster",privacy="approved_cloud",output_format="png")
            self.assertTrue(Path(result["path"]).is_file())
            self.assertEqual(Path(result["path"]).read_bytes(),b"fake-png")
            image_call=next(x for x in gateway.calls if x["path"]=="/images")
            self.assertNotIn("size",image_call["payload"])
            self.assertNotIn("aspect_ratio",image_call["payload"])
            self.assertEqual(image_call["payload"]["model"],"inclusionai/ming-image-0.1-design")
            self.assertTrue(result["preflight_zero_cost"])

    def test_image_generation_blocks_when_live_pricing_is_missing(self):
        with tempfile.TemporaryDirectory() as td:
            gateway=FakeGateway()
            for row in gateway.models:
                if row.get("id")=="inclusionai/ming-image-0.1-design":
                    row["pricing"]={}
            fabric=OpenRouterFreeFabric(gateway,td)
            with self.assertRaises(ZeroCostPolicyError):
                fabric.generate_image("unknown cost must stop",privacy="approved_cloud")

    def test_image_generation_blocks_when_live_price_is_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=OpenRouterFreeFabric(FakeGateway(image_cost="0.01"),td)
            with self.assertRaises(ZeroCostPolicyError):
                fabric.generate_image("do not charge",privacy="approved_cloud")

    def test_status_never_contains_api_key_and_reports_paid_fallback_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            fabric=OpenRouterFreeFabric(FakeGateway(),td)
            status=fabric.status(refresh=True)
            raw=json.dumps(status)
            self.assertNotIn("api_key",raw)
            self.assertEqual(status["paid_cloud_default"],"disabled")
            self.assertTrue(status["zero_cost_policy"]["live_catalog_preflight_required"])


if __name__=="__main__":
    unittest.main()
