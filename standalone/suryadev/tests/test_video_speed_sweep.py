"""True 1x, 1.5x, 2x, 3x comparisons use real source-time advancement."""
import unittest
from suryadev_video_speed_sweep import (
    RATES, speed_results, classify_sweep, detect_media_unload,
)
from suryadev_video_browser_probe import TRIAL_VIDEO


def video_samples(*, stall=None, ad_rate=None, actual_rate=None, media_error=None,
                  page=TRIAL_VIDEO):
    samples=[]
    base=100
    for idx,rate in enumerate(RATES):
        previous=0.0
        for step in range(9):
            t=base+idx*25+step*2
            delta=(actual_rate if actual_rate is not None else rate)*2
            seconds=previous if stall==rate else previous+delta
            if step==0:
                seconds=0.0
            previous=seconds
            samples.append({
                "phase_rate":rate,"seconds":seconds,
                "monotonic":float(t),
                "has_video":True,"paused":False,
                "playback_rate":(actual_rate if actual_rate is not None else rate),
                "ad_showing":ad_rate==rate,
                "media_error_code":media_error if step==4 and idx==0 else None,
                "ready_state":4,"network_state":2,"ended":False,
                "source_url":page,"requested_video_page":page==TRIAL_VIDEO,
            })
    return samples


class VideoSpeedSweepTests(unittest.TestCase):
    def test_all_four_real_rates_from_media_clock(self):
        result=classify_sweep(video_samples())
        self.assertTrue(result["all_speeds_verified"])
        self.assertEqual([r["requested_speed_x"] for r in result["speeds"]],
                         [1.0,1.5,2.0,3.0])
        for row,rate in zip(result["speeds"],RATES):
            self.assertTrue(row["pass"])
            self.assertAlmostEqual(row["effective_measured_speed_x"],rate,delta=0.01)

    def test_fake_dom_rate_without_media_advancement_fails(self):
        rows=speed_results(video_samples(stall=3.0))
        self.assertFalse(rows[-1]["pass"])
        self.assertEqual(rows[-1]["source_video_advanced_seconds"],0)

    def test_rate_clamped_to_two_cannot_pass_three(self):
        result=classify_sweep(video_samples(actual_rate=2.0))
        self.assertFalse(result["all_speeds_verified"])
        self.assertFalse(result["speeds"][-1]["pass"])

    def test_ad_only_phase_never_counts_towards_source_speed(self):
        result=classify_sweep(video_samples(ad_rate=1.5))
        self.assertFalse(result["speeds"][1]["pass"])
        self.assertGreater(result["advertisements_seen"],0)

    def test_media_errors_and_wrong_video_fail_even_if_clock_progresses(self):
        self.assertFalse(classify_sweep(
            video_samples(media_error=4))["all_speeds_verified"])
        self.assertFalse(classify_sweep(
            video_samples(page="https://www.youtube.com/watch?v=abcdefghijk")
        )["all_speeds_verified"])

    def test_exact_chrome_log_media_reset_causes_aborted_unload_classification(self):
        rows=video_samples()
        # Playback at 1x/1.5x is real. 2x briefly advances before the
        # documented 48.72s reset: readyState 4->0, networkState 2->0,
        # currentTime 53.9->0 and rate back to 1.
        for idx,row in enumerate(rows):
            if row["phase_rate"]==2.0 and row["monotonic"]>=156:
                row["seconds"]=0
                row["ready_state"]=0
                row["network_state"]=0
                row["playback_rate"]=1
                row["paused"]=False
                row["element_generation"]=2
            else:
                row["element_generation"]=1
        event=detect_media_unload(rows)
        self.assertIsNotNone(event)
        self.assertEqual(event["event"],"media_unloaded_after_playback")
        self.assertEqual(event["phase_rate"],2.0)
        self.assertTrue(event["video_element_replaced"])
        result=classify_sweep(rows)
        self.assertFalse(result["all_speeds_verified"])
        self.assertIsNotNone(result["media_unload_event"])

    def test_empty_video_does_not_count_as_three_x_content(self):
        rows=video_samples()
        for row in rows:
            if row["phase_rate"]==3.0:
                row.update({"seconds":0,"ready_state":0,"network_state":0,
                            "playback_rate":3,"paused":False})
        result=classify_sweep(rows)
        self.assertFalse(result["speeds"][-1]["pass"])
        self.assertEqual(result["speeds"][-1]["valid_content_wall_seconds"],0)
        self.assertEqual(result["speeds"][-1]["source_video_advanced_seconds"],0)

    def test_independent_two_x_can_pass_when_media_stays_ready(self):
        rows=[r for r in video_samples() if r["phase_rate"]==2.0]
        result=classify_sweep(rows,rates=(2.0,))
        self.assertEqual(len(result["speeds"]),1)
        self.assertTrue(result["all_speeds_verified"])
        self.assertTrue(result["speeds"][0]["pass"])

    def test_no_reset_during_startup_without_previous_content(self):
        rows=[{"seconds":0,"ready_state":0,"network_state":0,
               "phase_rate":2.0,"ad_showing":False,
               "requested_video_page":True},
              {"seconds":0,"ready_state":0,"network_state":0,
               "phase_rate":2.0,"ad_showing":False,
               "requested_video_page":True}]
        self.assertIsNone(detect_media_unload(rows))

    def test_no_learning_authority_is_asserted(self):
        r=classify_sweep(video_samples())
        self.assertFalse(r["learning_verified"])
        self.assertFalse(r["full_caption_or_audio_coverage_verified"])
        self.assertFalse(r["rishi_exam_verified"])


if __name__=="__main__":
    unittest.main()
