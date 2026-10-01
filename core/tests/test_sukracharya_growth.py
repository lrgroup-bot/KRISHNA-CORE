import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from krishna_core.sukracharya_growth import (
    SUKRACHARYA_SCHEMA,
    SukracharyaGrowthRishi,
    YOUTUBE_SEEDS,
)


class MemoryStub:
    def __init__(self):
        self.rows = []
    def audit(self, *args):
        self.rows.append(args)


class BrahmagyanStub:
    def __init__(self):
        self.claims = {
            "c1": {
                "claim_id": "c1",
                "claim": "A narrow pricing hypothesis has evidence.",
                "maturity": "L4",
                "evidence_status": "supported",
                "confidence": .8,
                "sources": [{
                    "title": "Primary source",
                    "url": "https://example.org/source",
                    "source_family": "example",
                    "source_type": "web",
                    "primary": True,
                }],
                "supporting_evidence": [],
                "qualifying_evidence": [],
                "contradicting_evidence": [],
            }
        }
    def claim(self, claim_id):
        return self.claims[claim_id]


class GarudaStub:
    def scout(self, project, query, limit):
        return {
            "web": [
                {
                    "title": "New growth video",
                    "url": "https://www.youtube.com/watch?v=new-growth",
                    "source": "youtube",
                }
            ]
        }


class LiveStub:
    def __init__(self):
        self.brahmagyan = BrahmagyanStub()
        self.garuda = GarudaStub()
        self.calls = []
    def run(self, project, topic, question, **kwargs):
        self.calls.append((project, topic, question, kwargs))
        return {
            "run": {"run_id": "run-1"},
            "mission": {
                "mission_id": "m1",
                "topic": topic,
                "question": question,
                "claim_ids": ["c1"],
            },
            "synthesis": {
                "summary": "Test the pricing hypothesis before scale.",
                "supported": ["narrow evidence"],
                "contested": ["generalization"],
                "unknowns": ["segment response"],
                "next_evidence": ["run price test"],
            },
            "test_plan": {"tests": [{"claim_id": "c1", "test": "pricing experiment"}]},
        }


class SuryadevStub:
    def __init__(self):
        self.jobs = []
    def create_job(self, kind, **kwargs):
        row = {"job_id": f"j{len(self.jobs)+1}", "kind": kind, **kwargs}
        self.jobs.append(row)
        return row


class SukracharyaGrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.live = LiveStub()
        self.surya = SuryadevStub()
        self.rishi = SukracharyaGrowthRishi(
            Path(self.tmp.name), rishi_live=self.live, suryadev=self.surya, memory=MemoryStub()
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_plan_is_advisory_and_requires_debate(self):
        plan = self.rishi.research_plan()
        self.assertEqual(plan["authority"], "advisory-only")
        self.assertIn("gautama", plan["debate_team"])
        self.assertTrue(plan["youtube_dynamic_discovery"] if "youtube_dynamic_discovery" in plan else plan["youtube_discovery_queries"])

    def test_dynamic_youtube_discovery_is_queued_through_suryadev(self):
        out = self.rishi.queue_youtube_learning(focus="pricing", limit=1)
        self.assertEqual(out["queued"], 1)
        self.assertEqual(self.surya.jobs[0]["kind"], "video_research")
        self.assertIn("timestamped transcript", self.surya.jobs[0]["instructions"])
        self.assertIn("youtube.com/watch", self.surya.jobs[0]["target"])

    def test_packet_preserves_sources_and_no_execution_authority(self):
        result = self.rishi.run_research(focus="pricing")
        packet = self.rishi.packet_from_run(result)
        self.assertEqual(packet["schema"], SUKRACHARYA_SCHEMA)
        self.assertEqual(packet["source"]["rishi"], "sukracharya")
        self.assertTrue(packet["debateRequired"])
        self.assertTrue(packet["sources"])
        self.assertIn("no execution authority", packet["decisionAuthority"])

    def test_cycle_can_run_without_network_share(self):
        out = self.rishi.cycle(focus="pricing", queue_video=False, share=False)
        self.assertEqual(out["packet"]["requestId"], "m1")
        self.assertTrue(out["delivery"]["skipped"])
        self.assertEqual(self.rishi.state["cycles"], 1)

    def test_seed_watchlist_exists_for_bootstrap(self):
        self.assertGreaterEqual(len(YOUTUBE_SEEDS), 3)
        self.assertTrue(all("youtube.com/watch" in x["url"] for x in YOUTUBE_SEEDS))


    def test_outbox_retry_delivers_and_clears_queue(self):
        packet = {"packetId": "retry-1", "schema": SUKRACHARYA_SCHEMA}
        self.rishi._queue_outbox(packet, "offline")

        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"ok":true,"duplicate":true}'

        with patch("krishna_core.sukracharya_growth.request.urlopen", return_value=Response()):
            result = self.rishi.retry_outbox()

        self.assertEqual(result["attempted"], 1)
        self.assertEqual(result["delivered"], 1)
        self.assertEqual(result["remaining"], 0)
        self.assertFalse(self.rishi.outbox_path.exists())


if __name__ == "__main__":
    unittest.main()
