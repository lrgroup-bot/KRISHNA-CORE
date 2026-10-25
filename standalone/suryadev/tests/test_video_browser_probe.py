"""Offline browser probe diagnostics: no video request, no notebook, no worker."""
import unittest

from suryadev_video_browser_probe import TRIAL_VIDEO, classify, validated_video


class VideoProbeTests(unittest.TestCase):
    def test_exact_reviewed_public_video_only(self):
        self.assertEqual(validated_video(TRIAL_VIDEO),TRIAL_VIDEO)
        for value in (
            "http://www.youtube.com/watch?v=VZ5LU8vHT0s",
            "https://www.youtube.com/watch?v=VZ5LU8vHT0s&t=50",
            "https://www.youtube.com/watch?v=abcdefghijk",
            "https://localhost/watch?v=VZ5LU8vHT0s",
            "https://user:pw@www.youtube.com/watch?v=VZ5LU8vHT0s",
            "https://www.youtube.com/"):
            with self.subTest(url=value),self.assertRaises(ValueError):
                validated_video(value)

    def test_healthy_content_clock_is_not_claimed_as_learning(self):
        row=classify([
            {"has_video":True,"ad_showing":False,"seconds":0,
             "media_error_code":None},
            {"has_video":True,"ad_showing":False,"seconds":35,
             "media_error_code":None}])
        self.assertTrue(row["content_clock_advanced_30s"])
        self.assertEqual(row["source_video_progress_seconds"],35)
        self.assertFalse(row["learning_verified"])
        self.assertFalse(row["rishi_exam_verified"])

    def test_advertisement_only_movement_is_not_content_progress(self):
        row=classify([
            {"has_video":True,"ad_showing":True,"seconds":0},
            {"has_video":True,"ad_showing":True,"seconds":70},
            {"has_video":True,"ad_showing":False,"seconds":0},
            {"has_video":True,"ad_showing":False,"seconds":8}])
        self.assertEqual(row["source_video_progress_seconds"],8)
        self.assertFalse(row["content_clock_advanced_30s"])
        self.assertTrue(row["advertisement_seen"])

    def test_no_media_or_codec_error_is_a_failure(self):
        row=classify([
            {"has_video":False,"ad_showing":False,"seconds":0,
             "media_error_code":None},
            {"has_video":True,"ad_showing":False,"seconds":8,
             "media_error_code":4}])
        self.assertFalse(row["content_clock_advanced_10s"])
        self.assertEqual(row["media_error_codes"],[4])


if __name__=="__main__":
    unittest.main()
