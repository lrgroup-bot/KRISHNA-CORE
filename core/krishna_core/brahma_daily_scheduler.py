from __future__ import annotations
import threading,time
from datetime import datetime
class BrahmaDailyScheduler:
 """Runs BRAHMA at most once per local calendar day; daemon, fail-soft."""
 def __init__(self,meeting_callable,snapshot_callable,interval_seconds=900):
  self.meeting=meeting_callable;self.snapshot=snapshot_callable
  self.interval=max(60,int(interval_seconds));self.last_date=None;self.last_report=None
  self._stop=threading.Event();self._thread=None
 def run_if_due(self,now=None):
  day=(now or datetime.now()).date().isoformat()
  if day==self.last_date:return {"ran":False,"reason":"already_ran","date":day}
  agents,proposals=self.snapshot()
  self.last_report=self.meeting(agents,proposals);self.last_date=day
  return {"ran":True,"date":day,"report":self.last_report}
 def start(self):
  if self._thread and self._thread.is_alive():return self.status()
  self._stop.clear()
  def loop():
   while not self._stop.is_set():
    try:self.run_if_due()
    except Exception:pass
    self._stop.wait(self.interval)
  self._thread=threading.Thread(target=loop,name="brahma-daily-council",daemon=True);self._thread.start()
  return self.status()
 def stop(self):self._stop.set();return self.status()
 def status(self):return {"running":bool(self._thread and self._thread.is_alive()),"last_date":self.last_date,"interval_seconds":self.interval}
