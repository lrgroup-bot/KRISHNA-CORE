import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import suryadev_worker
from krishna_core.suryadev import SuryadevAgent
from krishna_core.remote_access import PrivateRemotePolicy


class BrahmaStub:
    def __init__(self):
        self.calls=[]

    def intake(self, **kwargs):
        self.calls.append(kwargs)
        topic=str(kwargs.get("topic") or "")
        return {
            "decision_id":"brahma-"+str(len(self.calls)),
            "lead_rishi":"kashyapa" if "dna" in topic.lower() else "bharadvaja",
            "team":["kashyapa","gautama"] if "dna" in topic.lower() else ["bharadvaja","gautama"],
            "recorded_finding":{"finding_id":"rishi-"+str(len(self.calls))},
        }


class MemoryStub:
    def __init__(self):
        self.rows=[]

    def audit(self,*args):
        self.rows.append(args)


class SuryadevLearningPipelineTests(unittest.TestCase):
    def test_bundle_routes_to_existing_brahma_and_returns_cleanup_ack(self):
        with tempfile.TemporaryDirectory() as td:
            brahma=BrahmaStub()
            agent=SuryadevAgent(Path(td)/"surya",brahma=brahma,memory=MemoryStub())
            bundle={
                "schema":"krishna.suryadev.learning-bundle.v1",
                "job_id":"SURYA-test-1",
                "project":"BRAHMAGYAN",
                "source":{"url":"https://www.youtube.com/watch?v=test","title":"DNA repair lecture","subject":"DNA repair"},
                "learning_chunks":[{
                    "topic":"DNA repair",
                    "text":"The speaker described double-strand break repair as a research lead that requires independent verification.",
                    "start_seconds":10,
                    "end_seconds":600,
                    "modality":"video_caption_text",
                    "confidence":0.7,
                }],
                "visual_evidence":[{
                    "subject":"DNA repair",
                    "timestamp":"00h04m20s",
                    "sha256":"a"*64,
                    "reason":"diagram",
                    "research_question":"Which repair pathway is shown and what independent evidence supports it?",
                    "lab_relevance":True,
                }],
                "raw_media_included":False,
            }
            receipt=agent.route_learning_bundle(bundle,device_id="suryadev-ipad-01")
            self.assertTrue(receipt["cleanup_authorized"])
            self.assertEqual(receipt["accepted_chunks"],1)
            self.assertEqual(receipt["selected_visuals"],1)
            self.assertEqual(receipt["routed"][0]["lead_rishi"],"kashyapa")
            self.assertEqual(len(brahma.calls),1)
            self.assertFalse(brahma.calls[0]["provenance"]["raw_media_transferred"])

            replay=agent.route_learning_bundle(bundle,device_id="suryadev-ipad-01")
            self.assertTrue(replay["idempotent_replay"])
            self.assertEqual(replay["receipt_id"],receipt["receipt_id"])
            self.assertEqual(len(brahma.calls),1)

    def test_visual_only_bundle_is_candidate_not_invented_transcript(self):
        with tempfile.TemporaryDirectory() as td:
            brahma=BrahmaStub()
            agent=SuryadevAgent(Path(td)/"surya",brahma=brahma)
            bundle={
                "schema":"krishna.suryadev.learning-bundle.v1",
                "job_id":"SURYA-visual-1",
                "source":{"url":"https://example.org/video","title":"Microscope","subject":"cell structure"},
                "learning_chunks":[],
                "visual_evidence":[{
                    "subject":"cell structure",
                    "timestamp":"00h10m00s",
                    "sha256":"b"*64,
                    "reason":"microscope frame",
                    "research_question":"What observable structure is present?",
                    "lab_relevance":True,
                }],
                "raw_media_included":False,
            }
            receipt=agent.route_learning_bundle(bundle)
            self.assertEqual(receipt["accepted_chunks"],1)
            self.assertIn("Do not infer unseen/spoken claims",brahma.calls[0]["content"])

    def test_node_green_requires_recent_heartbeat_and_real_work_state(self):
        with tempfile.TemporaryDirectory() as td:
            agent=SuryadevAgent(Path(td)/"surya")
            hb=agent.device_heartbeat({
                "device_id":"ipad-01",
                "node_name":"SURYDEV iPad 01",
                "platform":"iPadOS",
                "worker_running":True,
                "network_online":True,
                "learning_state":"watching",
            })
            self.assertTrue(hb["server_link_green"])
            self.assertTrue(hb["suryadev_working_green"])
            self.assertTrue(hb["learning_green"])
            status=agent.device_status("ipad-01")
            self.assertTrue(status["connected"])

    def test_private_remote_policy_allows_only_bounded_suryadev_node_routes(self):
        policy=PrivateRemotePolicy()
        self.assertTrue(policy.mobile_route_allowed("/api/suryadev/device/heartbeat"))
        self.assertTrue(policy.mobile_route_allowed("/api/suryadev/device/status"))
        self.assertTrue(policy.mobile_route_allowed("/api/suryadev/learning-bundle"))
        self.assertFalse(policy.mobile_route_allowed("/api/suryadev/status"))

    def _job(self, path, job_id="SURYA-worker-1"):
        row={
            "schema":"krishna.suryadev.job.v1",
            "job_id":job_id,
            "kind":"video_research",
            "project":"BRAHMAGYAN",
            "target":"https://example.org/video",
            "constraints":{"duration_seconds":30},
        }
        Path(path).write_text(json.dumps(row),encoding="utf-8")
        return row

    def _adapter(self, path, produce_bundle=True):
        code=[
            "import json,sys",
            "from pathlib import Path",
            "job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))",
            "work=Path(sys.argv[2]);work.mkdir(parents=True,exist_ok=True)",
            "(work/'transcript').mkdir(exist_ok=True)",
            "(work/'frames').mkdir(exist_ok=True)",
            "(work/'transcript'/'transcript.txt').write_text('[00h00m10s] DNA repair',encoding='utf-8')",
            "(work/'frames'/'DNA__00h00m10s__diagram.jpg').write_bytes(b'frame')",
        ]
        if produce_bundle:
            code += [
                "bundle={'schema':'krishna.suryadev.learning-bundle.v1','job_id':job['job_id'],'source':{'url':job['target'],'title':'DNA','subject':'DNA'},'learning_chunks':[{'topic':'DNA','text':'Candidate transcript evidence','start_seconds':0,'end_seconds':30}],'visual_evidence':[{'subject':'DNA','timestamp':'00h00m10s','sha256':'%s','reason':'diagram','research_question':'verify diagram','lab_relevance':True}],'raw_media_included':False}" % ("c"*64),
                "(work/'learning-bundle.json').write_text(json.dumps(bundle),encoding='utf-8')",
            ]
        Path(path).write_text("\n".join(code),encoding="utf-8")

    def test_worker_requires_evidence_bundle_before_completion_and_is_restart_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"root";root.mkdir()
            job_path=Path(td)/"job.json";self._job(job_path)
            adapter=Path(td)/"adapter.py";self._adapter(adapter,True)
            env={
                "SURYADEV_JOB_ADAPTER":str(adapter),
                "SURYADEV_ADAPTER_PYTHON":sys.executable,
            }
            with patch.dict(os.environ,env,clear=False):
                first=suryadev_worker.process_job(job_path,root)
                self.assertEqual(first["status"],"AWAITING_SERVER_ACK")
                self.assertTrue(first["bundle_valid"])
                second=suryadev_worker.process_job(job_path,root)
                self.assertTrue(second["reused_durable_result"])
                self.assertEqual(second["bundle_sha256"],first["bundle_sha256"])

                with self.assertRaises(ValueError):
                    suryadev_worker.acknowledge(root,"SURYA-worker-1","bad","0"*64)
                self.assertTrue((root/"jobs"/"SURYA-worker-1"/"learning-bundle.json").is_file())

                ack=suryadev_worker.acknowledge(
                    root,"SURYA-worker-1","receipt-1",first["bundle_sha256"]
                )
                self.assertTrue(ack["ok"])
                self.assertFalse((root/"jobs"/"SURYA-worker-1"/"learning-bundle.json").exists())
                self.assertFalse((root/"jobs"/"SURYA-worker-1"/"transcript").exists())
                self.assertFalse((root/"jobs"/"SURYA-worker-1"/"frames").exists())
                self.assertTrue((root/"receipts"/"SURYA-worker-1.json").is_file())

    def test_adapter_exit_zero_without_learning_bundle_is_not_complete(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"root";root.mkdir()
            job_path=Path(td)/"job.json";self._job(job_path,"SURYA-worker-no-bundle")
            adapter=Path(td)/"adapter.py";self._adapter(adapter,False)
            with patch.dict(os.environ,{
                "SURYADEV_JOB_ADAPTER":str(adapter),
                "SURYADEV_ADAPTER_PYTHON":sys.executable,
            },clear=False):
                out=suryadev_worker.process_job(job_path,root)
            self.assertEqual(out["status"],"EVIDENCE_REQUIRED")
            self.assertFalse(out["ready_for_upload"])

    def test_video_adapter_contract_has_six_hour_limit_and_five_minute_finish_grace(self):
        root=Path(__file__).resolve().parents[2]
        source=(root/"scripts"/"SURYDEV_VIDEO_LEARNING_ADAPTER.py").read_text(encoding="utf-8")
        self.assertIn("6 * 3600",source)
        self.assertIn("finish_grace_seconds",source)
        self.assertIn("300",source)
        self.assertIn("transcript.txt",source)
        self.assertIn("visual_evidence",source)
        self.assertIn("lab-dossier",source)
        self.assertIn("questions_for_rishi_or_lab",source)
        self.assertIn("_SystemAudioASR",source)
        self.assertIn("pyaudiowpatch",source)
        self.assertIn("WhisperModel",source)
        self.assertIn("vad_filter=True",source)
        self.assertIn("source_video_downloaded",source)
        self.assertIn("False",source)


if __name__=="__main__":
    unittest.main()
