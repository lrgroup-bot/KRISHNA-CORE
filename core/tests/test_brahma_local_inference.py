"""Only TLS-pinned authenticated local AI; no cloud or model downloads."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from krishna_core.brahma_local_inference import LocalBrahmaInference

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"standalone"/"brahma"))
from local_ollama_gateway import infer, handler_factory, inference_admission

class FakeResponse:
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def read(self,size):
        return json.dumps({"response":"A local model response","done":True}).encode()

class LocalInferenceTests(unittest.TestCase):
    def test_gateway_calls_only_loopback_ollama_and_never_downloads(self):
        captured=[]
        def opener(req,timeout):
            captured.append((req.full_url,json.loads(req.data),timeout))
            return FakeResponse()
        r=infer({"model":"qwen3.5:4b","role":"rishi_exam_author",
                 "prompt":"Investigate why a transistor fails and specify a falsifiable laboratory test.",
                 "num_predict":2048},models={"qwen3.5:4b"},opener=opener)
        self.assertTrue(r["inference_local"])
        self.assertFalse(r["knowledge_verified"])
        self.assertEqual(captured[0][0],"http://127.0.0.1:11434/api/generate")
        self.assertEqual(captured[0][1]["stream"],False)
        self.assertEqual(captured[0][1]["model"],"qwen3.5:4b")
    def test_rejects_other_models_and_unbounded_requests(self):
        for data in (
            {"model":"unapproved","role":"rishi_research","prompt":"x"*90},
            {"model":"qwen3.5:4b","role":"arbitrary_action","prompt":"x"*90},
            {"model":"qwen3.5:4b","role":"rishi_research","prompt":"x"*13000},
            {"model":"qwen3.5:4b","role":"rishi_research","prompt":"x"*90,"num_predict":5000},
        ):
            with self.subTest(data=data.get("model")):
                with self.assertRaises(ValueError):
                    infer(data,models={"qwen3.5:4b"},opener=lambda *_:self.fail("network must not run"))
    def test_private_pinned_config_and_reject_public_cloud(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"token.txt").write_text("t"*64,encoding="utf-8")
            settings={"schema":"krishna.brahma.local-inference.v1",
                      "endpoint":"https://192.168.0.33:18787",
                      "cert_sha256":"a"*64,"model":"qwen3.5:4b",
                      "token_file":"token.txt"}
            (root/"config.json").write_text(json.dumps(settings),encoding="utf-8")
            client=LocalBrahmaInference(config_path=root/"config.json")
            self.assertEqual(client.model,"qwen3.5:4b")
            for external in ("https://8.8.8.8:18787","http://192.168.0.33:18787",
                             "https://example.com:18787"):
                settings["endpoint"]=external
                (root/"config.json").write_text(json.dumps(settings),encoding="utf-8")
                with self.assertRaises(ValueError):
                    LocalBrahmaInference(config_path=root/"config.json")
    def test_central_inference_refuses_85_percent_hardware_pressure(self):
        self.assertTrue(inference_admission(sampler=lambda:(30,44,60))["safe"])
        self.assertFalse(inference_admission(sampler=lambda:(85,44,60))["safe"])
        self.assertFalse(inference_admission(sampler=lambda:(30,85,60))["safe"])
        self.assertFalse(inference_admission(sampler=lambda:(30,44,85))["safe"])
        self.assertFalse(inference_admission(sampler=lambda:(None,44,60))["safe"])

    def test_requires_explicit_long_token(self):
        with self.assertRaises(ValueError):
            handler_factory(secret="short",models={"qwen3.5:4b"})

if __name__=="__main__":
    unittest.main()
