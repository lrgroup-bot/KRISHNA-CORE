from __future__ import annotations
import threading,time

class VoiceBargeInController:
    """Provider-neutral cancellation token for interruptible local speech playback."""
    def __init__(self,stop_playback=None,on_state=None):
        self.stop_playback=stop_playback;self.on_state=on_state;self._speaking=False;self._lock=threading.RLock();self.last_interrupt=None
    def speaking(self,active=True):
        with self._lock:self._speaking=bool(active)
        if self.on_state:self.on_state("SPEAKING" if active else "IDLE")
    def owner_speech_detected(self,confidence=1.0):
        with self._lock:
            if not self._speaking:return {"interrupted":False,"reason":"not_speaking"}
            self._speaking=False;self.last_interrupt={"at":time.time(),"confidence":float(confidence)}
        if self.stop_playback:self.stop_playback()
        if self.on_state:self.on_state("LISTENING")
        return {"interrupted":True,**self.last_interrupt}
    def status(self):
        with self._lock:return {"speaking":self._speaking,"last_interrupt":self.last_interrupt,"supports_barge_in":True}
