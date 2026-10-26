"""GARUDANETRA Media Lite owns only a bounded approved media context."""
from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from suryadev_garudanetra_media import (
    approved_youtube_watch, blocked_private_resource, MediaContinuity,
    GarudanetraMediaSession,
)


def frame(seconds, *, ready=4, network=2, generation=1,
          ad=False, ended=False, media_error=None):
    return {"seconds":seconds,"video_ready_state":ready,
            "video_network_state":network,
            "media_element_generation":generation,
            "ad_showing":ad,"ended":ended,"video_error_code":media_error}


class MediaContinuityTests(unittest.TestCase):
    def test_exact_approved_video_and_reject_unsafe_destinations(self):
        approved="https://www.youtube.com/watch?v=VZ5LU8vHT0s"
        self.assertEqual(approved_youtube_watch(approved),approved)
        for url in ("http://www.youtube.com/watch?v=VZ5LU8vHT0s",
                    "https://www.youtube.com/watch?v=VZ5LU8vHT0s&t=10",
                    "https://www.youtube.com/watch?v=invalid",
                    "https://127.0.0.1/watch?v=VZ5LU8vHT0s",
                    "https://user:secret@www.youtube.com/watch?v=VZ5LU8vHT0s"):
            with self.subTest(url=url),self.assertRaises(ValueError):
                approved_youtube_watch(url)

    def test_media_private_network_block_and_google_stream_access(self):
        for url in ("http://127.0.0.1:8766/health",
                    "https://192.168.0.1/config",
                    "https://10.4.3.1/internal",
                    "file:///etc/passwd",
                    "https://local-host.lan/api"):
            with self.subTest(url=url):
                self.assertTrue(blocked_private_resource(url))
        for url in ("https://www.youtube.com/watch?v=VZ5LU8vHT0s",
                    "https://r1---sn-xx.googlevideo.com/videoplayback",
                    "https://i.ytimg.com/vi/a/sddefault.jpg",
                    "blob:https://www.youtube.com/a"):
            with self.subTest(url=url):
                self.assertFalse(blocked_private_resource(url))

    def test_exact_operator_reset_is_not_silent_stall(self):
        guard=MediaContinuity(empty_tolerance=2)
        self.assertEqual(guard.observe(frame(45.54),wall_seconds=42.45),
                         "playing_or_buffered")
        self.assertEqual(guard.observe(frame(53.90),wall_seconds=46.72),
                         "playing_or_buffered")
        self.assertEqual(guard.observe(frame(0,ready=0,network=0),
                                       wall_seconds=48.72),"waiting_for_media")
        self.assertEqual(guard.observe(frame(0,ready=0,network=0),
                                       wall_seconds=50.73),"media_unloaded_after_playback")
        self.assertEqual(guard.last_event["last_source_seconds"],53.9)
        self.assertEqual(guard.last_event["ready_state_before"],4)
        self.assertEqual(guard.last_event["network_state_after"],0)
        self.assertTrue(guard.last_event["provider_cause_unverified"])

    def test_no_false_reset_during_initial_media_loading(self):
        guard=MediaContinuity()
        for _ in range(10):
            self.assertEqual(guard.observe(frame(0,ready=0,network=0)),
                             "waiting_for_media")
        self.assertIsNone(guard.last_event)

    def test_element_replacement_and_media_error_observed(self):
        guard=MediaContinuity()
        guard.observe(frame(35,generation=1),wall_seconds=20)
        self.assertEqual(guard.observe(frame(0.1,generation=2),
                                       wall_seconds=21),"video_element_replaced")
        self.assertTrue(guard.last_event["video_element_replaced"])
        self.assertEqual(guard.observe(frame(1,media_error=4)),
                         "media_error")

    def test_ads_not_counted_as_source_clock(self):
        guard=MediaContinuity()
        guard.observe(frame(60),wall_seconds=60)
        self.assertEqual(guard.observe(frame(61,ad=True),wall_seconds=61),
                         "advertisement")
        self.assertEqual(guard.last_content_seconds,60)
        self.assertIsNone(guard.last_event)


class FakeRoute:
    class Request:
        def __init__(self,url):
            self.url=url
    def __init__(self,url):
        self.request=self.Request(url)
        self.done=None
    def continue_(self):
        self.done="allowed"
    def abort(self):
        self.done="blocked"


class FakePage:
    def __init__(self):
        self.main_frame=object()
        self.listeners={}
        self.visited=None
    def on(self,event,callback):
        self.listeners[event]=callback
    def goto(self,url,**kwargs):
        self.visited=url
        self.listeners["framenavigated"](FakeFrame(self.main_frame,url))
    def close(self):
        pass


class FakeFrame:
    def __init__(self,identity,url):
        self.identity=identity
        self.url=url
    def __eq__(self,other):
        return self.identity==other


class FakeContext:
    def __init__(self):
        self.pages=[FakePage()]
        self.routes=[]
        self.closed=False
    def route(self,glob,callback):
        self.routes.append((glob,callback))
    def close(self):
        self.closed=True


class FakeChromium:
    def __init__(self,ctx):
        self.ctx=ctx
        self.args=[]
    def launch_persistent_context(self,*args,**kwargs):
        self.args.append((args,kwargs))
        return self.ctx


class MediaSessionTests(unittest.TestCase):
    def test_session_reuses_canonical_local_playwright_profile_and_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=FakeContext()
            chromium=FakeChromium(ctx)
            playwright=type("MockPlaywright",(),{"chromium":chromium})()
            session=GarudanetraMediaSession(
                tmp,"https://www.youtube.com/watch?v=VZ5LU8vHT0s",
                channel="chrome",headless=True)
            context,page=session.launch(playwright)
            self.assertIs(context,ctx)
            self.assertEqual(page.visited,session.source_url)
            self.assertEqual(session.diagnostics()["main_frame_navigations"],1)
            self.assertFalse(session.diagnostics()["unexpected_navigation"])
            self.assertEqual(chromium.args[0][1]["channel"],"chrome")
            private=FakeRoute("http://127.0.0.1:8766/health")
            external=FakeRoute("https://r2.googlevideo.com/media")
            session.route_sync(private)
            session.route_sync(external)
            self.assertEqual(private.done,"blocked")
            self.assertEqual(external.done,"allowed")
            session.close()
            self.assertTrue(ctx.closed)
            self.assertFalse(session.diagnostics()["source_learning_verified"])

    def test_same_video_unapproved_redirect_cannot_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx=FakeContext()
            session=GarudanetraMediaSession(
                tmp,"https://www.youtube.com/watch?v=VZ5LU8vHT0s")
            playwright=type("P",(),{"chromium":FakeChromium(ctx)})()
            _,page=session.launch(playwright)
            page.listeners["framenavigated"](
                FakeFrame(page.main_frame,"https://evil.example/?v=VZ5LU8vHT0s"))
            self.assertTrue(session.unexpected_navigation)
            session.close()


if __name__=="__main__":
    unittest.main()
