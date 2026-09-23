import json
import tempfile
import unittest
from pathlib import Path

from krishna_core.lab_bot import LabBot
from krishna_core.rishi_live_research import RishiLiveResearchExecutor


class _Memory:
    def __init__(self):self.events=[]
    def audit(self,*args):self.events.append(args)


class RishiRoleDispatchTests(unittest.TestCase):
    def test_rishi_model_helper_forwards_dedicated_role(self):
        calls=[]
        def model_call(prompt,**kwargs):
            calls.append(dict(kwargs))
            return {"provider":"fake","model":"fake-model","text":"{}"}
        with tempfile.TemporaryDirectory() as td:
            ex=RishiLiveResearchExecutor(
                Path(td),None,None,model_call,_Memory(),
            )
            out=ex._model(
                "review",privacy="approved_cloud",project="KRISHNA",
                actor="rishi-live-gautama",role="gautama_review",
            )
            self.assertEqual(out["role"],"gautama_review")
            self.assertEqual(out["provider"],"fake")
            self.assertEqual(calls[0]["role"],"gautama_review")

    def test_research_source_maps_each_phase_to_role_contract(self):
        source=Path(__file__).resolve().parents[1]/"krishna_core"/"rishi_live_research.py"
        text=source.read_text(encoding="utf-8")
        expected={
            "rishi-live-claim-extractor":"rishi_research",
            "rishi-live-classical-extractor":"rishi_research",
            "rishi-live-counter-evidence":"rishi_counter_evidence",
            "rishi-live-gautama":"gautama_review",
            "rishi-live-debate-":"rishi_debate",
            "rishi-live-gautama-debate":"gautama_review",
            "rishi-live-vyasa-debate":"vyasa_synthesis",
            "rishi-live-test-plan":"bharadvaja_test_plan",
            "rishi-live-final-vyasa":"vyasa_synthesis",
        }
        for actor,role in expected.items():
            with self.subTest(actor=actor,role=role):
                self.assertIn(actor,text)
                self.assertIn('"'+role+'"',text)


class LabAIRoleTests(unittest.TestCase):
    def _experiment(self,bot):
        return bot.request({
            "rishi":"kanada",
            "hypothesis":"Signal A changes measured response B.",
            "objective":"Measure B against a control condition.",
            "domain":"physics",
            "mode":"simulation",
            "controls":["negative control"],
            "measurements":["response B"],
            "success_criteria":["predefined difference exceeds uncertainty"],
            "source_refs":["paper:1"],
        })

    def test_hypothesis_assistance_is_unverified_and_role_aware(self):
        calls=[]
        def model_call(prompt,**kwargs):
            calls.append(dict(kwargs))
            return {
                "provider":"ollama","model":"local-test",
                "text":json.dumps({
                    "hypothesis":"Changing A changes B.",
                    "rationale":"Candidate derived from supplied context.",
                    "independent_variable":"A",
                    "dependent_variables":["B"],
                    "controls":["negative control"],
                    "measurements":["B"],
                    "falsification_criteria":["no reproducible change in B"],
                    "limitations":["single candidate"],
                }),
            }
        with tempfile.TemporaryDirectory() as td:
            bot=LabBot(Path(td))
            bot.bind_ai(model_call,memory=_Memory())
            out=bot.hypothesis_assist({
                "rishi":"kanada","topic":"signal response","question":"Does A change B?",
                "evidence_summary":"A cited paper reports an association.","source_refs":["paper:1"],
            })
            self.assertEqual(out["status"],"UNVERIFIED_HYPOTHESIS")
            self.assertEqual(out["role"],"lab_hypothesis")
            self.assertEqual(calls[0]["role"],"lab_hypothesis")
            self.assertIn("candidate only",out["policy"])

    def test_result_analysis_records_independent_local_and_cloud_reviews(self):
        def model_call(*args,**kwargs):
            raise AssertionError("pair callback should be used")
        def pair_call(prompt,**kwargs):
            self.assertEqual(kwargs["role"],"lab_result_analysis")
            return {
                "local_review":{
                    "provider":"ollama","model":"qwen-local",
                    "text":json.dumps({
                        "observations":["B increased in recorded measurement"],
                        "interpretation":"The run is consistent with the hypothesis.",
                        "contradictions":[],"limitations":["one run"],
                        "follow_up_tests":["independent replication"],
                        "conclusion_state":"SUPPORTED_BY_THIS_RUN_ONLY",
                    }),
                },
                "independent_cloud_review":{
                    "provider":"openrouter-free:reasoning","model":"dynamic-free",
                    "text":json.dumps({
                        "observations":["Recorded B differs from baseline"],
                        "interpretation":"Causation is not established.",
                        "contradictions":[],"limitations":["single simulated run"],
                        "follow_up_tests":["repeat with blinded control"],
                        "conclusion_state":"PRELIMINARY",
                    }),
                },
                "independent_pair":True,
                "errors":{},
            }
        with tempfile.TemporaryDirectory() as td:
            bot=LabBot(Path(td))
            bot.bind_ai(model_call,pair_call,_Memory())
            exp=self._experiment(bot)
            bot.record_result(exp["experiment_id"],{
                "kind":"measurement","summary":"B increased versus baseline",
                "measurements":[{"name":"B","value":1.2}],
            })
            out=bot.analyze_results(exp["experiment_id"],privacy="approved_cloud")
            self.assertEqual(out["status"],"UNVERIFIED_INTERPRETATION")
            self.assertTrue(out["independent_pair"])
            self.assertEqual(len(out["reviews"]),2)
            persisted=bot.get(exp["experiment_id"])
            self.assertEqual(len(persisted["ai_reviews"]),1)
            self.assertIn("not experimental evidence",out["policy"])

    def test_result_analysis_requires_actual_result_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            bot=LabBot(Path(td))
            bot.bind_ai(lambda *a,**k:{"text":"{}"})
            exp=self._experiment(bot)
            with self.assertRaisesRegex(ValueError,"no result evidence"):
                bot.analyze_results(exp["experiment_id"])


if __name__=="__main__":
    unittest.main()
