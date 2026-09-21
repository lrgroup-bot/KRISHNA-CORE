from __future__ import annotations

import json
import os
import shlex
import subprocess
import threading
import time
from pathlib import Path


class CommandTemplate:
    def __init__(self,raw:str|None):
        self.raw=str(raw or "").strip()
    def available(self):return bool(self.raw)
    def run(self,values:dict,timeout=180)->str:
        if not self.raw:raise RuntimeError("provider command is not configured")
        args=[part.format(**values) for part in shlex.split(self.raw,posix=os.name!="nt")]
        p=subprocess.run(args,capture_output=True,text=True,shell=False,timeout=timeout)
        if p.returncode:raise RuntimeError((p.stderr or p.stdout)[-4000:])
        return p.stdout.strip()


class IndicConformerSTT:
    """AI4Bharat IndicConformer command boundary for Odia speech recognition.

    KRISHNA does not download large speech models implicitly. Configure
    KRISHNA_INDIC_STT_CMD with a local worker command containing {audio}.
    """
    def __init__(self,command=None):
        self.command=CommandTemplate(command or os.getenv("KRISHNA_INDIC_STT_CMD"))
    def status(self):
        return {"provider":"ai4bharat-indicconformer","language":"odia","local":True,
                "available":self.command.available(),"config":"KRISHNA_INDIC_STT_CMD"}
    def transcribe(self,audio_path):
        path=Path(audio_path)
        if not path.is_file():raise FileNotFoundError(str(path))
        out=self.command.run({"audio":str(path.resolve()),"language":"or"})
        try:
            data=json.loads(out)
            return str(data.get("text") or data.get("transcript") or "").strip()
        except json.JSONDecodeError:
            return out.strip()


class IndicTTS:
    """AI4Bharat Indic-TTS command boundary for local Odia speech synthesis.

    Configure KRISHNA_INDIC_TTS_CMD with {text}, {output} and optionally {language}.
    """
    def __init__(self,command=None):
        self.command=CommandTemplate(command or os.getenv("KRISHNA_INDIC_TTS_CMD"))
    def status(self):
        return {"provider":"ai4bharat-indic-tts","language":"odia","local":True,
                "available":self.command.available(),"config":"KRISHNA_INDIC_TTS_CMD"}
    def speak(self,text,output_path=None):
        text=str(text or "").strip()
        if not text:raise ValueError("text is required")
        output=Path(output_path or "krishna-odia.wav").resolve()
        self.command.run({"text":text,"output":str(output),"language":"or"})
        if not output.is_file():raise RuntimeError("Odia TTS command did not create output audio")
        return str(output)


class WakeWordService:
    """Optional always-listening local openWakeWord service.

    A custom KRISHNA wake-word model is mandatory. Audio never leaves the device.
    Sensitive actions are still authenticated separately by device/policy gates.
    """

    def __init__(self,model_path=None,threshold=None,on_wake=None):
        self.model_path=Path(model_path or os.getenv("KRISHNA_WAKEWORD_MODEL","")) if (model_path or os.getenv("KRISHNA_WAKEWORD_MODEL")) else None
        self.threshold=float(threshold if threshold is not None else os.getenv("KRISHNA_WAKEWORD_THRESHOLD","0.65"))
        self.on_wake=on_wake
        self._thread=None;self._stop=threading.Event();self.last_score=0.0;self.last_wake=0.0;self.error=None

    def dependency_status(self):
        openwake=False;sound=False;numpy=False
        try:import openwakeword;openwake=True
        except ImportError:pass
        try:import sounddevice;sound=True
        except ImportError:pass
        try:import numpy;numpy=True
        except ImportError:pass
        model=bool(self.model_path and self.model_path.is_file())
        return {"openwakeword":openwake,"sounddevice":sound,"numpy":numpy,"custom_model":model}

    def status(self):
        dep=self.dependency_status()
        return {"provider":"openwakeword","wake_word":"Krishna","local":True,
                "available":all(dep.values()),"running":bool(self._thread and self._thread.is_alive()),
                "threshold":self.threshold,"model_path":str(self.model_path) if self.model_path else None,
                "dependencies":dep,"last_score":self.last_score,"last_wake":self.last_wake,"error":self.error,
                "security_note":"wake word is an activation signal, not authentication"}

    def start(self):
        if self._thread and self._thread.is_alive():return self.status()
        dep=self.dependency_status()
        if not all(dep.values()):raise RuntimeError("openWakeWord runtime requires openwakeword, sounddevice, numpy and a custom KRISHNA model")
        self._stop.clear();self.error=None
        self._thread=threading.Thread(target=self._loop,name="krishna-wakeword",daemon=True);self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():self._thread.join(timeout=3)
        return self.status()

    def _loop(self):
        try:
            import numpy as np
            import sounddevice as sd
            from openwakeword.model import Model
            model=Model(wakeword_models=[str(self.model_path)])
            cooldown=0.0
            with sd.RawInputStream(samplerate=16000,blocksize=1280,dtype="int16",channels=1) as stream:
                while not self._stop.is_set():
                    data,overflowed=stream.read(1280)
                    audio=np.frombuffer(data,dtype=np.int16)
                    pred=model.predict(audio)
                    score=max([float(v) for v in pred.values()] or [0.0])
                    self.last_score=score
                    now=time.time()
                    if score>=self.threshold and now>=cooldown:
                        self.last_wake=now;cooldown=now+2.0
                        if self.on_wake:
                            try:self.on_wake({"score":score,"at":now})
                            except Exception as exc:
                                self.error=f"wake_callback: {type(exc).__name__}: {exc}"
        except Exception as exc:
            self.error=f"{type(exc).__name__}: {exc}"
        finally:
            self._stop.set()


class KrishnaVoiceStack:
    def __init__(self,on_wake=None):
        self.stt=IndicConformerSTT()
        self.tts=IndicTTS()
        self.wake=WakeWordService(on_wake=on_wake)
    def status(self):
        return {"stt":self.stt.status(),"tts":self.tts.status(),"wake":self.wake.status(),
                "language":"or-IN","mode":"local-first","authentication":"device/policy gate remains authoritative"}
