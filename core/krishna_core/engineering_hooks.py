from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Any, Callable


HOOKS = (
    "before_project", "after_intake", "before_worker", "after_worker",
    "before_write", "after_write", "before_test", "after_test",
    "before_merge", "after_merge", "before_release", "after_release",
    "on_failure", "on_rollback", "on_worker_retire",
)


class EngineeringHooks:
    """Small trusted lifecycle extension point.

    Hooks observe or enforce existing KRISHNA policy; they do not grant permissions
    or bypass Shared Action/Sudarshan approval.
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable[[dict[str, Any]], Any]]] = defaultdict(list)
        self._lock = RLock()

    def register(self, hook: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        if hook not in HOOKS:
            raise ValueError("unsupported engineering hook: " + str(hook))
        if not callable(handler):
            raise TypeError("hook handler must be callable")
        with self._lock:
            self._handlers[hook].append(handler)

    def emit(self, hook: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if hook not in HOOKS:
            raise ValueError("unsupported engineering hook: " + str(hook))
        with self._lock:
            handlers = tuple(self._handlers.get(hook, ()))
        results = []
        for handler in handlers:
            try:
                results.append({"ok": True, "result": handler(dict(payload or {}))})
            except Exception as exc:
                results.append({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
        return {
            "hook": hook,
            "handlers": len(handlers),
            "results": results,
            "authority": "KRISHNA/Sudarshan",
        }

    def status(self) -> dict[str, Any]:
        with self._lock:
            counts = {name: len(self._handlers.get(name, ())) for name in HOOKS}
        return {"component": "KRISHNA Engineering Hooks", "hooks": counts, "permissions_granted": False}
