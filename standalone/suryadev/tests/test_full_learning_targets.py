"""No-network safety contract for operator-requested source workload targets."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from suryadev_trial_limits import (
    VIDEO_FILE, trial_cap, select_trial_videos, video_job_id,
)
from suryadev_video_speed_sweep import RATES, EXPERIMENTAL_RATES, classify_sweep
from suryadev_video_browser_probe import TRIAL_VIDEO


URLS = [
    "https://www.youtube.com/watch?v=abcdefghijk",
    "https://www.youtube.com/watch?v=123456789ab",
    "https://www.youtube.com/watch?v=mgBpcQRDtl0",
    "https://www.youtube.com/watch?v=VZ5LU8vHT0s",
]


class OperatorLearningTargetsTests(unittest.TestCase):
    def test_five_fresh_video_selection_resumes_without_rewriting_approval(self):
        urls = URLS + ["https://www.youtube.com/watch?v=ZZZZZZZZZZZ"]
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"SURYADEV_TRIAL_VIDEO_COUNT": "5"}):
                selected = select_trial_videos(folder, urls, previously_tried=lambda _: False)
            self.assertEqual(len(selected), 5)
            path = Path(folder) / VIDEO_FILE
            original = path.read_bytes()
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(select_trial_videos(folder, urls, previously_tried=lambda _: False), selected)
            self.assertEqual(path.read_bytes(), original)

    def test_absent_profile_preserves_current_limits(self):
        with patch.dict(os.environ, {}, clear=True):
            for name in ("website","pdf","book","video"):
                self.assertIsNone(trial_cap(name))

    def test_requested_caps_are_bounded_and_bad_values_fail_closed(self):
        for kind,(env,maximum) in {
            "website":("SURYADEV_TRIAL_WEBSITE_TARGET",5),
            "pdf":("SURYADEV_TRIAL_PDF_TARGET",10),
            "book":("SURYADEV_TRIAL_BOOK_TARGET",5),
            "video":("SURYADEV_TRIAL_VIDEO_COUNT",5),
        }.items():
            with patch.dict(os.environ,{env:str(maximum)}):
                self.assertEqual(trial_cap(kind),maximum)
            for invalid in ("0",str(maximum+1),"no","-1","1.5"):
                with patch.dict(os.environ,{env:invalid}):
                    self.assertEqual(trial_cap(kind),0)

    def test_video_trial_selection_is_persistent_and_never_replays(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            tried={video_job_id(URLS[0])}
            with patch.dict(os.environ,{"SURYADEV_TRIAL_VIDEO_COUNT":"3"}):
                selected=select_trial_videos(root,URLS,
                    previously_tried=lambda x:x in tried)
                self.assertEqual(selected,{
                    video_job_id(URLS[1]),video_job_id(URLS[2]),
                    video_job_id(URLS[3])})
                original=(root/VIDEO_FILE).read_bytes()
                second=select_trial_videos(root,URLS,
                    previously_tried=lambda _:False)
                self.assertEqual(second,selected)
                self.assertEqual((root/VIDEO_FILE).read_bytes(),original)
                shrunk=select_trial_videos(root,[URLS[1]],
                    previously_tried=lambda _:False)
                self.assertEqual(shrunk,{video_job_id(URLS[1])})
                self.assertEqual((root/VIDEO_FILE).read_bytes(),original)

    def test_no_backfill_after_previous_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ,{"SURYADEV_TRIAL_VIDEO_COUNT":"3"}):
                first=select_trial_videos(folder,URLS[:2],
                    previously_tried=lambda _:False)
                self.assertEqual(len(first),2)
                later=select_trial_videos(folder,URLS,
                    previously_tried=lambda _:False)
                self.assertEqual(len(later),2)

    def test_empty_manifest_can_be_repaired_once_without_prior_replay(self):
        # Legacy code misclassified staged-only inbox jobs as attempts,
        # freezing an empty selection even though approved URLs were fresh.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            tried={video_job_id(URLS[0]),video_job_id(URLS[1]),
                   video_job_id(URLS[2])}
            with patch.dict(os.environ,{"SURYADEV_TRIAL_VIDEO_COUNT":"3"}):
                self.assertEqual(select_trial_videos(root, URLS,
                    previously_tried=lambda _:True),frozenset())
                original=(root/VIDEO_FILE).read_bytes()
                recovered=select_trial_videos(root,URLS,
                    previously_tried=lambda j:j in tried,recover_empty=True)
                self.assertEqual(recovered,{video_job_id(URLS[3])})
                backups=list(root.glob(
                    "video-trial-selection.before-empty-repair-*.json"))
                self.assertEqual(len(backups),1)
                self.assertEqual(backups[0].read_bytes(),original)
                repaired=json.loads((root/VIDEO_FILE).read_text())
                self.assertTrue(repaired["repaired_from_empty"])
                self.assertEqual(repaired["job_ids"],[video_job_id(URLS[3])])
                # A later approval cannot backfill a frozen nonempty selection.
                self.assertEqual(select_trial_videos(root,URLS[::-1],
                    previously_tried=lambda _:False,recover_empty=True),recovered)
                self.assertEqual(len(list(root.glob(
                    "video-trial-selection.before-empty-repair-*.json"))),1)

    def test_saved_empty_trial_resumes_without_repeating_launch_target(self):
        # Regression from physical laptop: automatic-video flag was present
        # but --video-target was omitted on the next startup. Only the
        # original saved approval may be reused; completed attempts stay out.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            tried={video_job_id(URLS[0]), video_job_id(URLS[1]),
                   video_job_id(URLS[2])}
            with patch.dict(os.environ, {"SURYADEV_TRIAL_VIDEO_COUNT":"3"}):
                self.assertEqual(select_trial_videos(root, URLS,
                    previously_tried=lambda _:True),frozenset())
            original=(root/VIDEO_FILE).read_bytes()
            with patch.dict(os.environ, {}, clear=True):
                selected=select_trial_videos(root, URLS,
                    previously_tried=lambda jid:jid in tried,recover_empty=True)
                self.assertEqual(selected,{video_job_id(URLS[3])})
                self.assertEqual(select_trial_videos(root, URLS[::-1],
                    previously_tried=lambda _:False,recover_empty=True),selected)
                self.assertEqual(len(list(root.glob(
                    "video-trial-selection.before-empty-repair-*.json"))),1)
                self.assertEqual(next(root.glob(
                    "video-trial-selection.before-empty-repair-*.json")).read_bytes(),
                    original)
            self.assertEqual(json.loads((root/VIDEO_FILE).read_text())["target"],3)

    def test_absent_trial_without_saved_manifest_does_not_create_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {}, clear=True):
                self.assertIsNone(select_trial_videos(
                    folder,URLS,previously_tried=lambda _:False,
                    recover_empty=True))
            self.assertFalse((Path(folder)/VIDEO_FILE).exists())

    def test_saved_corrupt_or_changed_target_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/VIDEO_FILE
            for payload in (
                {"schema":"suryadev.video-trial-selection.v1","target":True,"job_ids":[]},
                {"schema":"suryadev.video-trial-selection.v1","target":10,"job_ids":[]},
                {"schema":"suryadev.video-trial-selection.v1","target":3,"job_ids":["bad"]},
            ):
                file.write_text(json.dumps(payload),encoding="utf-8")
                before=file.read_bytes()
                with patch.dict(os.environ, {}, clear=True):
                    with self.assertRaises(RuntimeError):
                        select_trial_videos(folder, URLS,
                            previously_tried=lambda _:False,recover_empty=True)
                self.assertEqual(file.read_bytes(),before)
            file.write_text(json.dumps({
                "schema":"suryadev.video-trial-selection.v1","target":3,"job_ids":[]}),encoding="utf-8")
            with patch.dict(os.environ, {"SURYADEV_TRIAL_VIDEO_COUNT":"2"}):
                with self.assertRaises(RuntimeError):
                    select_trial_videos(folder, URLS,
                        previously_tried=lambda _:False,recover_empty=True)

    def test_empty_repair_never_selects_previously_attempted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.dict(os.environ,{"SURYADEV_TRIAL_VIDEO_COUNT":"3"}):
                select_trial_videos(root,URLS,previously_tried=lambda _:True)
                original=(root/VIDEO_FILE).read_bytes()
                self.assertEqual(select_trial_videos(root, URLS,
                    previously_tried=lambda _:True,recover_empty=True),frozenset())
                self.assertEqual((root/VIDEO_FILE).read_bytes(),original)
                self.assertFalse(list(root.glob(
                    "video-trial-selection.before-empty-repair-*.json")))

    def test_corrupted_selection_fails_closed_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/VIDEO_FILE
            file.write_text("[]",encoding="utf-8")
            with patch.dict(os.environ,{"SURYADEV_TRIAL_VIDEO_COUNT":"3"}):
                with self.assertRaises(RuntimeError):
                    select_trial_videos(folder,URLS,previously_tried=lambda _:False)
            self.assertEqual(file.read_text(encoding="utf-8"),"[]")

    def test_four_x_is_only_an_isolated_measured_probe(self):
        self.assertNotIn(4.0,RATES)
        self.assertEqual(EXPERIMENTAL_RATES,(4.0,))
        samples=[]
        for i in range(9):
            samples.append({
                "phase_rate":4.0, "seconds":i*8.0,
                "monotonic":100+i*2.0,"has_video":True,
                "paused":False,"playback_rate":4.0,"ad_showing":False,
                "media_error_code":None,"ready_state":4,"network_state":2,
                "requested_video_page":True,"source_url":TRIAL_VIDEO
            })
        verdict=classify_sweep(samples,rates=(4.0,))
        self.assertTrue(verdict["speeds"][0]["pass"])
        self.assertTrue(verdict["all_speeds_verified"])
        self.assertFalse(verdict["learning_verified"])
        self.assertFalse(verdict["full_caption_or_audio_coverage_verified"])


if __name__=="__main__":
    unittest.main()
