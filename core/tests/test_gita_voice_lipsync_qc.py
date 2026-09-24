from __future__ import annotations

import os
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from krishna_core.gita_gyan import GitaGyan
from krishna_core.gita_lipsync import GitaLipSyncPlanner
from krishna_core.gita_performance import GitaPerformanceEngine
from krishna_core.native_voice import SanskritTTS


ROOT = Path(__file__).resolve().parents[2]


class GitaLipSyncPlannerTests(unittest.TestCase):
    def test_all_required_languages_emit_only_supported_visemes_and_remain_unverified(self):
        samples={
            "sa":"कर्मण्येवाधिकारस्ते मा फलेषु कदाचन ।",
            "or":"ପାର୍ଥ, ଶାନ୍ତ ହୋଇ ଶୁଣ।",
            "hi":"पार्थ, शांत होकर सुनो।",
            "en":"Partha, listen calmly.",
        }
        for language,text in samples.items():
            out=GitaLipSyncPlanner.plan(text,language)
            self.assertEqual(out["language"],language)
            self.assertTrue(out["events"])
            self.assertFalse(out["verified"])
            self.assertEqual(out["verification_status"],"ESTIMATED_NOT_VERIFIED")
            for event in out["events"]:
                self.assertIn(event["viseme"],GitaLipSyncPlanner.VISEMES)
                self.assertLessEqual(event["start_ms"],event["end_ms"])

    def test_real_wav_duration_is_used_when_available(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"sample.wav"
            rate=16000
            with wave.open(str(path),"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate)
                wav.writeframes(b"\x00\x00"*rate)
            out=GitaLipSyncPlanner.plan("कर्म", "sa", path)
            self.assertEqual(out["timing_source"],"wav_duration_distributed")
            self.assertGreaterEqual(out["duration_ms"],995)
            self.assertLessEqual(out["duration_ms"],1005)
            self.assertEqual(out["events"][-1]["end_ms"],out["duration_ms"])

    def test_status_does_not_claim_forced_alignment_or_production_rig(self):
        status=GitaLipSyncPlanner.status()
        self.assertFalse(status["forced_alignment_verified"])
        self.assertFalse(status["production_rig_verified"])
        self.assertEqual(status["status"],"ESTIMATED_NOT_VERIFIED")


class SanskritVoiceBoundaryTests(unittest.TestCase):
    def test_sanskrit_voice_is_local_separate_and_unverified_until_acceptance(self):
        with patch.dict(os.environ,{"KRISHNA_SANSKRIT_TTS_CMD":""},clear=False):
            voice=SanskritTTS(command="")
            status=voice.status()
        self.assertEqual(status["languages"],["sa"])
        self.assertTrue(status["local"])
        self.assertTrue(status["offline_execution"])
        self.assertFalse(status["available"])
        self.assertFalse(status["verified_pronunciation"])
        self.assertIn("third-party",status["voice_identity"])

    def test_worker_forces_offline_execution_and_requires_local_assets(self):
        worker=(ROOT/"scripts"/"voice"/"sanskrit_tts_worker.py").read_text(encoding="utf-8-sig")
        self.assertIn('env["HF_HUB_OFFLINE"]="1"',worker)
        self.assertIn('env["TRANSFORMERS_OFFLINE"]="1"',worker)
        self.assertIn('bundle/"models"/"IndicF5"/"model.safetensors"',worker)
        self.assertIn('"voice_note":"Third-party Sanskrit reference recitation;',worker)

    def test_installer_is_e_drive_isolated_and_has_no_paid_fallback(self):
        script=(ROOT/"scripts"/"INSTALL_KRISHNA_SANSKRIT_TTS.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('E:\\Krishna-The GOD',script)
        self.assertIn('$voiceRoot=Join-Path $RuntimeRoot "voice"',script)
        self.assertIn('$envRoot=Join-Path $voiceRoot "envs\\sanskrit-tts"',script)
        self.assertIn('7d5b0b162477e1c2489c72da3ab2e3052c9a59bd',script)
        self.assertIn('13f7c4d627cc10111aea8fe9c0039462cacacdc7',script)
        self.assertIn('-SanskritTtsCommand',script)
        self.assertIn('No paid fallback',script)


class GitaPerformanceQCTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.gita=GitaGyan(Path(self.temp.name)/"gita")
        self.performance=GitaPerformanceEngine(self.gita)

    def tearDown(self):
        self.temp.cleanup()

    def test_all_700_records_have_full_micro_performance_contract(self):
        required={
            "blink_style","mouth_viseme_profile","neck_movement","shoulder_state",
            "torso_posture","arm_movement","body_energy_level","breathing_tempo",
            "gaze_relationship","scene_profile","speaking_tempo","renderer_claim",
        }
        records=self.performance.all_records()
        self.assertEqual(len(records),700)
        for record in records:
            self.assertTrue(required.issubset(record))
            self.assertEqual(record["renderer_claim"],"COMMAND_ONLY_UNTIL_ASSET_VERIFIED")
            self.assertFalse(self.performance.validate_record(record),record["verse_id"])

    def test_chapter_11_has_revelation_transition_cosmic_and_return_phases(self):
        self.assertEqual(self.performance.record(11,1)["avatar_family"],"DIVINE_REVEALER")
        self.assertEqual(self.performance.record(11,5)["avatar_family"],"VISHVARUPA_TRANSITION")
        self.assertEqual(self.performance.record(11,8)["avatar_family"],"VISHVARUPA_TRANSITION")
        self.assertEqual(self.performance.record(11,32)["avatar_family"],"VISHVARUPA")
        self.assertEqual(self.performance.record(11,50)["avatar_family"],"REASSURING_PERSONAL_FORM")
        self.assertEqual(self.performance.record(11,55)["avatar_family"],"REASSURING_PERSONAL_FORM")

    def test_qc_rejects_unprovenanced_or_incompatible_animation(self):
        record=self.performance.record(2,47)
        record["scriptural_evidence"]=[]
        self.assertIn("missing_textual_provenance",self.performance.validate_record(record))
        self.assertIn("missing_animation_provenance",self.performance.validate_record(record))

        record=self.performance.record(11,32)
        record["avatar_family"]="FLUTE_KRISHNA"
        record["background_profile"]="VRINDAVAN_FOREST"
        self.assertIn("incompatible_vrindavan_battlefield_styling",self.performance.validate_record(record))

        record=self.performance.record(2,47)
        record["movement_intensity"]="controlled_high"
        self.assertIn("excessive_animation",self.performance.validate_record(record))

    def test_qc_report_remains_green_for_generated_records(self):
        report=self.performance.qc_report()
        self.assertTrue(report["valid"],report["failures"][:10])
        self.assertEqual(report["record_count"],700)


class GitaVoiceApiContractTests(unittest.TestCase):
    def test_server_uses_separate_sanskrit_provider_and_never_claims_verified_audio_or_lipsync(self):
        server=(ROOT/"core"/"krishna_core"/"server.py").read_text(encoding="utf-8-sig")
        self.assertIn("_voice.sanskrit.speak",server)
        self.assertIn('provider="edge-sanskrit-tts"',server)
        self.assertIn('payload["sanskrit_audio_generated"]',server)
        self.assertIn('payload["sanskrit_audio_verified"]=False',server)
        self.assertIn('payload["lip_sync_verified"]=False',server)
        self.assertIn("GitaLipSyncPlanner.plan",server)

    def test_voice_setup_persists_separate_sanskrit_command(self):
        script=(ROOT/"scripts"/"SETUP_KRISHNA_VOICE.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("SanskritTtsCommand",script)
        self.assertIn("KRISHNA_SANSKRIT_TTS_CMD",script)


if __name__=="__main__":
    unittest.main()
