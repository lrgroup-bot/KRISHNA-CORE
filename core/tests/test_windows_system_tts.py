import subprocess
import os
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.native_voice import WindowsSystemTTS


class WindowsSystemTTSTests(unittest.TestCase):
    def test_speech_text_cannot_become_powershell_code(self):
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/"voice.wav"
            text="Hello'; Remove-Item E:\\example; $(anything)"
            def run(args,**kwargs):
                self.assertNotIn(text,args[-1])
                self.assertEqual(kwargs["env"]["KRISHNA_TTS_TEXT"],text)
                self.assertNotIn("shell",kwargs)
                output.write_bytes(b"RIFF"+b"x"*80)
                return subprocess.CompletedProcess(args,0,"","")
            with patch("krishna_core.native_voice.os",SimpleNamespace(name="nt",environ=os.environ)),patch("krishna_core.native_voice.subprocess.run",side_effect=run):
                self.assertEqual(WindowsSystemTTS().speak(text,output),str(output))

    def test_success_without_audio_is_reported_as_failure(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("krishna_core.native_voice.os",SimpleNamespace(name="nt",environ=os.environ)),patch("krishna_core.native_voice.subprocess.run",return_value=subprocess.CompletedProcess([],0,"","")):
                with self.assertRaisesRegex(RuntimeError,"did not produce audio"):
                    WindowsSystemTTS().speak("Hello",Path(td)/"missing.wav")
