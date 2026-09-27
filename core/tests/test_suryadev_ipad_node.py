import tempfile
import unittest
from pathlib import Path

from krishna_core.rishi_council import RishiCouncil
from krishna_core.suryadev import SuryadevAgent
from krishna_core.remote_access import PrivateRemotePolicy


class BrahmaPodcastStub:
    def intake(self, **kwargs):
        return {
            "lead_rishi": "shravana",
            "team": ["shravana", "gautama", "veda-vyasa"],
            "recorded_finding": {"finding_id": "rishi-podcast-1"},
        }


class SuryadevIPadNodeTests(unittest.TestCase):
    def test_shravana_is_permanent_podcast_specialist(self):
        council=RishiCouncil()
        profile=council.get("shravana")
        self.assertEqual(profile["display_name"],"Rishi Shravana")
        self.assertIn("podcast",profile["domains"])
        selected=council.select("podcast long-form interview transcript analysis",4)
        self.assertEqual(selected[0]["id"],"shravana")

    def test_top30_queue_has_thirty_approved_items(self):
        with tempfile.TemporaryDirectory() as td:
            agent=SuryadevAgent(Path(td))
            queue=agent.podcast_queue()
            self.assertEqual(queue["count"],30)
            self.assertEqual(queue["rishi"],"shravana")
            self.assertTrue(all(x["approved"] for x in queue["items"]))
            self.assertTrue(all("youtube" in x["youtube_search"] for x in queue["items"]))

    def test_heartbeat_truth_lights_require_actual_playback(self):
        with tempfile.TemporaryDirectory() as td:
            agent=SuryadevAgent(Path(td))
            base={
                "device_id":"suryadev-ipad-test",
                "node_name":"SURYADEV SHRAVANA — Podcast Gurukul",
                "network_online":True,
                "screen_awake":True,
                "app_state":"foreground",
                "youtube_url":"https://www.youtube.com/watch?v=abc",
                "battery_percent":90,
            }
            stopped=agent.device_heartbeat({**base,"youtube_playing":False})
            self.assertTrue(stopped["krishna_link_green"])
            self.assertFalse(stopped["suryadev_working_green"])
            playing=agent.device_heartbeat({**base,"youtube_playing":True})
            self.assertTrue(playing["suryadev_working_green"])
            self.assertFalse(playing["rishi_learning_green"])

    def test_arbitrary_youtube_video_cannot_turn_learning_green(self):
        with tempfile.TemporaryDirectory() as td:
            agent=SuryadevAgent(Path(td),brahma=BrahmaPodcastStub())
            out=agent.podcast_learning({
                "device_id":"suryadev-ipad-test",
                "source_url":"https://www.youtube.com/watch?v=abc",
                "title":"Random video",
                "queue_show":"Not In The Queue",
                "visible_caption_text":"This is enough transcript evidence to otherwise be eligible for learning.",
            })
            self.assertFalse(out["accepted"])
            self.assertFalse(out["learning_green"])
            self.assertEqual(out["reason"],"not_approved_top30_podcast_queue")

    def test_approved_podcast_routes_to_shravana_and_turns_learning_green(self):
        with tempfile.TemporaryDirectory() as td:
            agent=SuryadevAgent(Path(td),brahma=BrahmaPodcastStub())
            agent.device_heartbeat({
                "device_id":"suryadev-ipad-test",
                "network_online":True,
                "screen_awake":True,
                "app_state":"foreground",
                "youtube_playing":True,
                "youtube_url":"https://www.youtube.com/watch?v=abc",
            })
            show=agent.podcast_queue()["items"][0]["show"]
            text=("The guest explains a concrete mechanism, gives examples, and makes several factual "
                  "claims that need independent verification before being treated as durable knowledge.")
            out=agent.podcast_learning({
                "device_id":"suryadev-ipad-test",
                "source_url":"https://www.youtube.com/watch?v=abc",
                "title":"Full podcast episode",
                "queue_show":show,
                "start_seconds":10,
                "end_seconds":100,
                "visible_caption_text":text,
            })
            self.assertTrue(out["accepted"])
            self.assertTrue(out["routed_to_rishi"])
            self.assertTrue(out["learning_green"])
            self.assertEqual(out["lead_rishi"],"shravana")
            status=agent.device_status("suryadev-ipad-test")
            self.assertTrue(status["rishi_learning_green"])
            self.assertEqual(status["last_learning_title"],"Full podcast episode")

    def test_podcast_without_enough_caption_evidence_stays_red(self):
        with tempfile.TemporaryDirectory() as td:
            agent=SuryadevAgent(Path(td),brahma=BrahmaPodcastStub())
            show=agent.podcast_queue()["items"][0]["show"]
            out=agent.podcast_learning({
                "device_id":"suryadev-ipad-test",
                "source_url":"https://www.youtube.com/watch?v=abc",
                "title":"Podcast",
                "queue_show":show,
                "visible_caption_text":"too short",
            })
            self.assertTrue(out["accepted"])
            self.assertFalse(out["routed_to_rishi"])
            self.assertFalse(out["learning_green"])

    def test_suryadev_mobile_routes_are_private_paired_routes(self):
        policy=PrivateRemotePolicy()
        for path in (
            "/api/suryadev/device/heartbeat",
            "/api/suryadev/device/alert",
            "/api/suryadev/device/learning",
            "/api/suryadev/device/research",
            "/api/suryadev/device/status",
            "/api/suryadev/podcast/queue",
        ):
            self.assertTrue(policy.mobile_route_allowed(path),path)

    def test_ipad_source_contract_has_visible_node_and_three_truth_lights(self):
        root=Path(__file__).resolve().parents[2]
        source=(root/"ios"/"SURYDEV"/"main.swift").read_text(encoding="utf-8")
        plist=(root/"ios"/"SURYDEV"/"Info.plist").read_text(encoding="utf-8")
        self.assertIn("NODE ID · ",source)
        self.assertIn('StatusLamp("KRISHNA LINK")',source)
        self.assertIn('StatusLamp("SURYADEV WORKING")',source)
        self.assertIn('StatusLamp("RISHI LEARNING")',source)
        self.assertIn("UIApplication.shared.isIdleTimerDisabled = true",source)
        self.assertIn("battery.50",source)
        self.assertIn("WHAT I LEARNED",source)
        self.assertIn("GARUDANETRA WEB",source)
        self.assertIn("Top 30 Podcast Queue",source)
        self.assertIn("<integer>2</integer>",plist)
        self.assertNotIn("<integer>1</integer>",plist)

    def test_android_receives_suryadev_alerts_from_session_bus(self):
        root=Path(__file__).resolve().parents[2]
        activity=(root/"mobile_v3"/"MainActivity.java").read_text(encoding="utf-8")
        ui=(root/"mobile_v3"/"index.html").read_text(encoding="utf-8")
        self.assertIn('"suryadev.alert"',activity)
        self.assertIn('"KRISHNA · SURYADEV"',activity)
        self.assertIn("e.type==='suryadev.alert'",ui)
        self.assertIn("e.type==='suryadev.learning'",ui)


if __name__=="__main__":
    unittest.main()
