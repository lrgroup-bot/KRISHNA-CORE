from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class SanskritParlerContractTests(unittest.TestCase):
    def test_worker_is_local_sanskrit_specific_and_low_vram_safe(self):
        text=(ROOT/"scripts"/"voice"/"sanskrit_parler_worker.py").read_text(encoding="utf-8-sig")
        self.assertIn("ai4bharat/indic-parler-tts-pretrained",text)
        self.assertIn('"speaker":"Aryan"',text)
        self.assertIn("total >= 6.0",text)
        self.assertIn('return "cuda" if total >= 6.0 else "cpu"',text)
        self.assertIn("local_files_only=True",text)

    def test_installer_is_isolated_e_drive_and_fail_closed_on_gated_access(self):
        text=(ROOT/"scripts"/"INSTALL_KRISHNA_SANSKRIT_TTS.ps1").read_text(encoding="utf-8-sig")
        self.assertIn(r'voice\envs\sanskrit-tts',text)
        self.assertIn('$voiceRoot=Join-Path $RuntimeRoot "voice"',text)
        self.assertIn(r'models\sanskrit-parler',text)
        self.assertIn("HF_HOME",text)
        self.assertIn("exit 7",text)
        self.assertIn("SanskritTtsCommand",text)
        self.assertIn("Production Core venv unchanged",text)
        self.assertIn("& $ttsPy -m pip install",text)
        self.assertNotIn('$RuntimeRoot+"\\.venv"',text)
        self.assertIn("local_files_only=True",(ROOT/"scripts"/"voice"/"sanskrit_parler_worker.py").read_text(encoding="utf-8-sig"))


if __name__=="__main__":
    unittest.main()
