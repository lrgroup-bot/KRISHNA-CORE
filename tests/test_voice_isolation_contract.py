from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class VoiceIsolationContractTests(unittest.TestCase):
    def test_core_supports_external_local_wake_worker(self):
        text=(ROOT/"core"/"krishna_core"/"native_voice.py").read_text(encoding="utf-8-sig")
        for token in (
            "class ExternalWakeWordService",
            'KRISHNA_WAKEWORD_CMD',
            "subprocess.Popen(",
            "shell=False",
            "external-local-wake",
        ):
            self.assertIn(token,text)
        self.assertIn("ExternalWakeWordService(wake_command,on_wake=on_wake)",text)

    def test_setup_does_not_modify_core_venv_by_default(self):
        text=(ROOT/"scripts"/"SETUP_KRISHNA_VOICE.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("$InstallEmbeddedWakeDependencies",text)
        self.assertIn("if($InstallEmbeddedWakeDependencies)",text)
        self.assertIn("KRISHNA_WAKEWORD_CMD",text)
        self.assertIn("Production Core venv left unchanged",text)

    def test_voice_setup_preserves_existing_provider_settings(self):
        text=(ROOT/"scripts"/"SETUP_KRISHNA_VOICE.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("$values=[ordered]@{}",text)
        self.assertIn("$assignmentPattern=",text)
        self.assertIn("Get-Content -LiteralPath $envFile",text)
        self.assertIn('KRISHNA_WAKEWORD_CMD',text)
        self.assertIn('KRISHNA_INDIC_STT_CMD',text)
        self.assertIn('KRISHNA_INDIC_TTS_CMD',text)
        self.assertIn('$values.Keys | Sort-Object',text)
        self.assertNotIn('. $envFile',text)

    def test_sanskrit_tts_is_separate_local_provider(self):
        core=(ROOT/"core"/"krishna_core"/"native_voice.py").read_text(encoding="utf-8-sig")
        setup=(ROOT/"scripts"/"SETUP_KRISHNA_VOICE.ps1").read_text(encoding="utf-8-sig")
        installer=(ROOT/"scripts"/"INSTALL_KRISHNA_SANSKRIT_TTS.ps1").read_text(encoding="utf-8-sig")
        worker=(ROOT/"scripts"/"voice"/"sanskrit_tts_worker.py").read_text(encoding="utf-8-sig")
        self.assertIn("class SanskritChantTTS",core)
        self.assertIn("KRISHNA_SANSKRIT_TTS_CMD",core)
        self.assertIn("KRISHNA_SANSKRIT_TTS_CMD",setup)
        self.assertIn("envs\\\\sanskrit-tts",installer)
        self.assertIn("Hari7718/EdgeSanskrit-TTS",installer)
        self.assertIn("7d5b0b162477e1c2489c72da3ab2e3052c9a59bd",installer)
        self.assertIn("Production Core venv",installer)
        self.assertIn("shell=False",worker)
        self.assertIn("generate_sanskrit_v2.py",worker)

    def test_isolated_wake_installer_targets_runtime_voice_env(self):
        text=(ROOT/"scripts"/"INSTALL_KRISHNA_WAKE_RUNTIME.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('voice',text)
        self.assertIn('envs\\wake',text)
        self.assertIn("openwakeword sounddevice numpy",text)
        self.assertIn("Core venv was not modified",text)
        self.assertIn("-WakeCommand $cmd",text)

    def test_worker_emits_bounded_json_wake_event(self):
        text=(ROOT/"scripts"/"voice"/"krishna_wake_worker.py").read_text(encoding="utf-8-sig")
        self.assertIn('RawInputStream(',text)
        self.assertIn('"event":"wake"',text)
        self.assertIn('"wake_word":"Krishna"',text)
        self.assertIn("score>=args.threshold",text)


if __name__=="__main__":
    unittest.main()
