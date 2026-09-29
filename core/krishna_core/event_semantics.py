from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable


class EventSemantics:
    """Tiny event-composition helpers inspired by plugin microkernels.

    No threads or workers are resident. Parallel executors exist only for the
    duration of one call.
    """

    VERSION="event-semantics-v1"

    @staticmethod
    def serial(value: Any, handlers: list[Callable]) -> list[Any]:
        results=[]
        current=value
        for handler in handlers or []:
            current=handler(current)
            results.append(current)
        return results

    @staticmethod
    def waterfall(value: Any, handlers: list[Callable]) -> Any:
        current=value
        for handler in handlers or []:
            candidate=handler(current)
            if candidate is not None:
                current=candidate
        return current

    @staticmethod
    def parallel(value: Any, handlers: list[Callable], max_workers=4) -> list[Any]:
        callbacks=list(handlers or [])
        if not callbacks:return []
        workers=max(1,min(int(max_workers),len(callbacks),8))
        ordered=[None]*len(callbacks)
        with ThreadPoolExecutor(max_workers=workers,thread_name_prefix="krishna-event") as pool:
            futures={pool.submit(fn,value):idx for idx,fn in enumerate(callbacks)}
            for future in as_completed(futures):
                ordered[futures[future]]=future.result()
        return ordered

    @staticmethod
    def emit(value: Any, handlers: list[Callable]) -> list[dict]:
        # "emit" remains bounded and synchronous in KRISHNA core. Subsystems that
        # require durable asynchronous delivery must use the DurableEventBus.
        out=[]
        for handler in handlers or []:
            try:
                handler(value);out.append({"ok":True})
            except Exception as exc:
                out.append({"ok":False,"error":f"{type(exc).__name__}: {exc}"})
        return out

    @classmethod
    def status(cls):
        return {
            "component":"KRISHNA Event Semantics",
            "version":cls.VERSION,
            "resident_workers":0,
            "modes":{
                "serial":"ordered gates/checkpoints",
                "waterfall":"bounded transform chain",
                "parallel":"temporary fan-out for independent observers",
                "emit":"best-effort notification; durable work uses DurableEventBus",
            },
        }
