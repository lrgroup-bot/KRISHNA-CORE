from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class IndicVoiceWorkerContractTests(unittest.TestCase):
    def test_tts_worker_supports_only_hindi_and_odia(self):
        text=(ROOT/"scripts"/"voice"/"indic_tts_worker.py").read_text(encoding="utf-8-sig")
        self.assertIn('LANGUAGES = {"hi", "or"}',text)
        self.assertIn("TTS.bin.synthesize",text)
        self.assertIn("shell=False",text)
        self.assertIn("config.krishna.json",text)

    def test_tts_installer_is_e_drive_isolated_and_pinned(self):
        text=(ROOT/"scripts"/"INSTALL_KRISHNA_INDIC_TTS.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('$voiceRoot=Join-Path $RuntimeRoot "voice"',text)
        self.assertIn('envs\\indic-tts',text)
        self.assertIn('models\\indic-tts',text)
        self.assertIn("8efcb8adaaf55563538c12e325d073eaf110065d",text)
        self.assertIn("v1-checkpoints-release/$lang.zip",text)
        self.assertIn("-IndicTtsCommand $cmd",text)
        self.assertIn("Production Core venv unchanged",text)

    def test_stt_worker_matches_official_multilingual_conformer_contract(self):
        text=(ROOT/"scripts"/"voice"/"indicconformer_worker.py").read_text(encoding="utf-8-sig")
        self.assertIn('LANGUAGES = {"hi", "or"}',text)
        self.assertIn("AutoModel.from_pretrained",text)
        self.assertIn("trust_remote_code=True",text)
        self.assertIn('args.decoder',text)

    def test_stt_installer_fails_closed_for_gated_model(self):
        text=(ROOT/"scripts"/"INSTALL_KRISHNA_INDIC_STT.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("ai4bharat/indic-conformer-600m-multilingual",text)
        self.assertIn('$voiceRoot=Join-Path $RuntimeRoot "voice"',text)
        self.assertIn('envs\\indic-stt',text)
        self.assertIn("KRISHNA_HF_ACCESS_BLOCKED",text)
        self.assertIn("No STT command was activated",text)
        self.assertIn("-IndicSttCommand $cmd",text)
        self.assertIn("Production Core venv unchanged",text)


if __name__=="__main__":
    unittest.main()
