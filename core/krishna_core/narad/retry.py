from __future__ import annotations

import time


def run_with_retry(fn,policy,on_attempt=None):
    attempts=[]
    max_attempts=int(policy.max_attempts)
    for index in range(1,max_attempts+1):
        started=time.perf_counter()
        try:
            value=fn(index)
            attempts.append({"attempt":index,"ok":True,"elapsed_ms":int((time.perf_counter()-started)*1000)})
            if on_attempt:on_attempt(attempts[-1])
            return value,attempts
        except Exception as exc:
            row={"attempt":index,"ok":False,"elapsed_ms":int((time.perf_counter()-started)*1000),
                 "error":f"{type(exc).__name__}: {exc}"}
            attempts.append(row)
            if on_attempt:on_attempt(row)
            if index>=max_attempts:raise
            delay=(policy.delay_ms/1000.0)*(policy.backoff**(index-1))
            if delay:time.sleep(min(delay,10.0))
