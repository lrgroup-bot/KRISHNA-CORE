from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path

from .command_line import split_command


class CommandTemplate:
    def __init__(self,raw:str|None):
        self.raw=str(raw or "").strip()
    def available(self):return bool(self.raw)
    def run(self,values:dict,timeout=180)->str:
        if not self.raw:raise RuntimeError("provider command is not configured")
        args=[part.format(**values) for part in split_command(self.raw,empty_message="provider command is not configured")]
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
    LANGUAGES={"or":"odia","hi":"hindi"}
    def status(self):
        return {"provider":"ai4bharat-indicconformer","language":"odia","languages":list(self.LANGUAGES),
                "local":True,"available":self.command.available(),"config":"KRISHNA_INDIC_STT_CMD",
                "note":"IndicConformer covers Hindi and Odia here; English speech input uses the browser/OS fallback unless a separate local worker is configured."}
    def transcribe(self,audio_path,language="or"):
        path=Path(audio_path)
        if not path.is_file():raise FileNotFoundError(str(path))
        lang=str(language or "or").strip().lower()
        if lang not in self.LANGUAGES:raise ValueError("IndicConformer language must be one of: hi, or")
        out=self.command.run({"audio":str(path.resolve()),"language":lang})
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
    KNOWN_LANGUAGES={"or":"odia","hi":"hindi","en":"english"}
    def configured_languages(self):
        raw=os.getenv("KRISHNA_INDIC_TTS_LANGUAGES","hi,or")
        langs=[]
        for value in raw.split(","):
            lang=value.strip().lower()
            if lang in self.KNOWN_LANGUAGES and lang not in langs:langs.append(lang)
        return langs or ["hi","or"]
    def status(self):
        languages=self.configured_languages()
        return {"provider":"ai4bharat-indic-tts","language":"odia","languages":languages,
                "known_languages":list(self.KNOWN_LANGUAGES),"local":True,"available":self.command.available(),
                "config":"KRISHNA_INDIC_TTS_CMD","language_config":"KRISHNA_INDIC_TTS_LANGUAGES",
                "note":"Hindi/Odia are the KRISHNA defaults. The official Indic-TTS release also publishes English checkpoints; KRISHNA advertises English only when the configured local worker declares en."}
    def speak(self,text,output_path=None,language="or"):
        text=str(text or "").strip()
        if not text:raise ValueError("text is required")
        lang=str(language or "or").strip().lower()
        configured=self.configured_languages()
        if lang not in configured:raise ValueError("local Indic-TTS language is not configured: "+lang)
        output=Path(output_path or ("krishna-"+lang+".wav")).resolve()
        self.command.run({"text":text,"output":str(output),"language":lang})
        if not output.is_file():raise RuntimeError("local TTS command did not create output audio")
        return str(output)


class SanskritTTS:
    """Dedicated local Sanskrit shloka-recitation boundary.

    Sanskrit is intentionally separate from conversational Indic-TTS so KRISHNA
    never pretends an Odia/Hindi prose voice is a verified Sanskrit recitation
    model. Configure KRISHNA_SANSKRIT_TTS_CMD with {text} and {output}.
    """

    def __init__(self,command=None):
        self.command=CommandTemplate(command or os.getenv("KRISHNA_SANSKRIT_TTS_CMD"))

    def status(self):
        return {
            "provider":"local-sanskrit-recitation",
            "language":"sa",
            "languages":["sa"],
            "local":True,
            "available":self.command.available(),
            "config":"KRISHNA_SANSKRIT_TTS_CMD",
            "note":"Dedicated Sanskrit recitation worker; no silent Hindi/Odia fallback.",
        }

    def speak(self,text,output_path=None):
        text=str(text or "").strip()
        if not text:raise ValueError("text is required")
        output=Path(output_path or "krishna-sa.wav").resolve()
        self.command.run({"text":text,"output":str(output),"language":"sa"})
        if not output.is_file():raise RuntimeError("local Sanskrit TTS command did not create output audio")
        return str(output)


class ExternalWakeWordService:
    """Run wake-word detection in an isolated local worker process.

    KRISHNA Core never imports the worker's ML/audio dependencies. The worker
    emits one JSON line per activation, for example:
    {"event":"wake","wake_word":"Krishna","score":0.91,"at":1234567890.0}
    """

    def __init__(self,command=None,on_wake=None):
        self.raw=str(command or os.getenv("KRISHNA_WAKEWORD_CMD") or "").strip()
        self.on_wake=on_wake
        self._thread=None
        self._proc=None
        self._stop=threading.Event()
        self.last_score=0.0
        self.last_wake=0.0
        self.error=None

    def status(self):
        return {
            "provider":"external-local-wake",
            "wake_word":"Krishna",
            "local":True,
            "available":bool(self.raw),
            "running":bool(self._thread and self._thread.is_alive() and self._proc and self._proc.poll() is None),
            "config":"KRISHNA_WAKEWORD_CMD",
            "last_score":self.last_score,
            "last_wake":self.last_wake,
            "error":self.error,
            "security_note":"wake word is an activation signal, not authentication",
        }

    def start(self):
        if self._thread and self._thread.is_alive():
            return self.status()
        if not self.raw:
            raise RuntimeError("external wake worker command is not configured")
        split_command(self.raw,empty_message="external wake worker command is not configured")
        self._stop.clear()
        self.error=None
        self._thread=threading.Thread(target=self._loop,name="krishna-wakeword-external",daemon=True)
        self._thread.start()
        return self.status()

    def stop(self):
        self._stop.set()
        proc=self._proc
        if proc and proc.poll() is None:
            try:proc.terminate()
            except Exception:pass
            try:proc.wait(timeout=2)
            except Exception:
                try:proc.kill()
                except Exception:pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        return self.status()

    def _loop(self):
        proc=None
        try:
            args=split_command(self.raw,empty_message="external wake worker command is not configured")
            proc=subprocess.Popen(
                args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,bufsize=1,shell=False,
            )
            self._proc=proc
            while not self._stop.is_set():
                line=proc.stdout.readline() if proc.stdout else ""
                if not line:
                    if proc.poll() is not None:break
                    time.sleep(0.05)
                    continue
                try:
                    event=json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(event.get("event") or "").strip().lower() not in {"wake","krishna_detected"}:
                    continue
                try:score=float(event.get("score",1.0))
                except (TypeError,ValueError):score=1.0
                now=float(event.get("at") or time.time())
                self.last_score=max(0.0,min(1.0,score))
                self.last_wake=now
                payload=dict(event)
                payload.setdefault("score",self.last_score)
                payload.setdefault("at",now)
                if self.on_wake:
                    try:self.on_wake(payload)
                    except Exception as exc:
                        self.error=f"wake_callback: {type(exc).__name__}: {exc}"
            if proc.poll() not in (None,0) and not self._stop.is_set():
                detail=""
                try:detail=(proc.stderr.read() if proc.stderr else "")[-2000:]
                except Exception:pass
                self.error=f"wake_worker_exit={proc.returncode}: {detail}".strip()
        except Exception as exc:
            self.error=f"{type(exc).__name__}: {exc}"
        finally:
            self._proc=None
            self._stop.set()


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
        self.sanskrit_tts=SanskritTTS()
        wake_command=os.getenv("KRISHNA_WAKEWORD_CMD")
        self.wake=ExternalWakeWordService(wake_command,on_wake=on_wake) if wake_command else WakeWordService(on_wake=on_wake)
    def status(self):
        return {"stt":self.stt.status(),"tts":self.tts.status(),"sanskrit_tts":self.sanskrit_tts.status(),"wake":self.wake.status(),
                "language":"or-IN","global_conversation_language":"or","mode":"local-first","authentication":"device/policy gate remains authoritative"}
