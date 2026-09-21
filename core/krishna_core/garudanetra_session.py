from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


@dataclass
class BrowserSession:
    session_id: str
    project: str
    requested_url: str
    state: str = "STARTING"
    current_url: str = ""
    title: str = ""
    paused: bool = False
    owner_control: bool = False
    stopped: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_error: str | None = None
    viewport: dict = field(default_factory=lambda: {"width": 1280, "height": 800})
    visible_text: str = ""
    console: list[dict] = field(default_factory=list)
    network: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    frame: bytes | None = None


class GarudanetraSessionManager:
    """Persistent private Chromium sessions for KRISHNA's live-work browser panel.

    Playwright is imported only inside the worker so Core can start honestly even when
    the optional browser runtime is unavailable. Session state is kept in memory and
    private contexts are destroyed on stop.
    """

    def __init__(self, runtime_root: str | Path, headless: bool = True, timeout_ms: int = 15000):
        self.root = Path(runtime_root)
        self.headless = bool(headless)
        self.timeout_ms = int(timeout_ms)
        self._lock = threading.RLock()
        self._sessions: dict[str, BrowserSession] = {}
        self._commands: dict[str, queue.Queue] = {}
        self._threads: dict[str, threading.Thread] = {}

    @staticmethod
    def validate_url(url: str) -> str:
        value = str(url or "").strip()
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Garudanetra requires an http:// or https:// URL")
        return value

    def create(self, project: str, url: str) -> dict:
        target = self.validate_url(url)
        sid = str(uuid.uuid4())
        session = BrowserSession(session_id=sid, project=str(project or "KRISHNA"), requested_url=target)
        with self._lock:
            self._sessions[sid] = session
            self._commands[sid] = queue.Queue(maxsize=100)
        thread = threading.Thread(target=self._worker, args=(sid,), name=f"garudanetra-{sid[:8]}", daemon=True)
        self._threads[sid] = thread
        thread.start()
        return self.status(sid)

    def _get(self, session_id: str) -> BrowserSession:
        with self._lock:
            session = self._sessions.get(str(session_id))
        if not session:
            raise KeyError("Garudanetra session not found")
        return session

    def status(self, session_id: str | None = None) -> dict:
        if session_id:
            session = self._get(session_id)
            with self._lock:
                return self._snapshot(session)
        with self._lock:
            rows = [self._snapshot(s) for s in self._sessions.values()]
        rows.sort(key=lambda x: x["created_at"], reverse=True)
        return {"sessions": rows[:20], "count": len(rows)}

    @staticmethod
    def _snapshot(session: BrowserSession) -> dict:
        return {
            "session_id": session.session_id,
            "project": session.project,
            "requested_url": session.requested_url,
            "state": session.state,
            "current_url": session.current_url,
            "title": session.title,
            "paused": session.paused,
            "owner_control": session.owner_control,
            "stopped": session.stopped,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "last_error": session.last_error,
            "viewport": dict(session.viewport),
            "visible_text": session.visible_text[:6000],
            "console": list(session.console[-50:]),
            "network": list(session.network[-100:]),
            "findings": list(session.findings[-100:]),
            "frame_available": bool(session.frame),
        }

    def frame(self, session_id: str) -> bytes | None:
        session = self._get(session_id)
        with self._lock:
            return bytes(session.frame) if session.frame else None

    def command(self, session_id: str, action: str, payload: dict | None = None) -> dict:
        session = self._get(session_id)
        action = str(action or "").strip().lower()
        if action not in {"pause", "resume", "takeover", "stop", "navigate", "click", "fill", "press", "click_xy", "scroll"}:
            raise ValueError(f"unsupported Garudanetra action: {action}")
        if session.stopped:
            raise RuntimeError("Garudanetra session is already stopped")
        q = self._commands[session.session_id]
        try:
            q.put_nowait({"action": action, "payload": dict(payload or {})})
        except queue.Full as exc:
            raise RuntimeError("Garudanetra command queue is full") from exc
        return self.status(session.session_id)

    def close_all(self):
        with self._lock:
            ids = list(self._sessions)
        for sid in ids:
            try:
                if not self._get(sid).stopped:
                    self.command(sid, "stop")
            except Exception:
                pass

    def _append_console(self, sid: str, kind: str, text: str):
        session = self._get(sid)
        with self._lock:
            session.console.append({"type": str(kind), "text": str(text)[:1000], "at": time.time()})
            del session.console[:-200]
            if str(kind).lower() == "error":
                session.findings.append({"kind": "console_error", "detail": str(text)[:1000], "severity": "error"})

    def _append_network(self, sid: str, method: str, url: str, status: int):
        session = self._get(sid)
        with self._lock:
            session.network.append({"method": method, "url": str(url)[:1500], "status": int(status), "at": time.time()})
            del session.network[:-400]
            if int(status) >= 400:
                session.findings.append({"kind": "http_error", "detail": f"{status} {url}"[:1200], "severity": "error"})

    def _worker(self, sid: str):
        session = self._get(sid)
        browser = context = page = None
        playwright_cm = None
        try:
            from playwright.sync_api import sync_playwright
            playwright_cm = sync_playwright()
            p = playwright_cm.start()
            try:
                browser = p.chromium.launch(channel="chrome", headless=self.headless)
            except Exception:
                browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport=dict(session.viewport),
                accept_downloads=False,
                java_script_enabled=True,
            )
            page = context.new_page()
            page.set_default_timeout(self.timeout_ms)
            page.on("console", lambda msg: self._append_console(sid, msg.type, msg.text))
            page.on("pageerror", lambda exc: self._append_console(sid, "pageerror", str(exc)))
            page.on("response", lambda resp: self._append_network(sid, resp.request.method, resp.url, resp.status))
            with self._lock:
                session.state = "NAVIGATING"
                session.updated_at = time.time()
            page.goto(session.requested_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            with self._lock:
                session.state = "LIVE"
                session.current_url = page.url
                session.title = page.title()
                session.updated_at = time.time()

            last_capture = 0.0
            last_text = 0.0
            while True:
                now = time.time()
                try:
                    cmd = self._commands[sid].get(timeout=0.12)
                    action, payload = cmd["action"], cmd["payload"]
                    if action == "stop":
                        with self._lock:
                            session.state = "STOPPING"
                        break
                    if action == "pause":
                        with self._lock:
                            session.paused = True
                            session.owner_control = False
                            session.state = "PAUSED"
                    elif action == "resume":
                        with self._lock:
                            session.paused = False
                            session.owner_control = False
                            session.state = "LIVE"
                    elif action == "takeover":
                        with self._lock:
                            session.paused = True
                            session.owner_control = True
                            session.state = "OWNER_CONTROL"
                    elif action == "navigate":
                        target = self.validate_url(payload.get("url"))
                        page.goto(target, wait_until="domcontentloaded", timeout=self.timeout_ms)
                    elif action == "click":
                        page.locator(str(payload.get("selector") or "")).click()
                    elif action == "fill":
                        page.locator(str(payload.get("selector") or "")).fill(str(payload.get("value") or ""))
                    elif action == "press":
                        page.locator(str(payload.get("selector") or "body")).press(str(payload.get("key") or "Enter"))
                    elif action == "click_xy":
                        nx = min(1.0, max(0.0, float(payload.get("x", 0.5))))
                        ny = min(1.0, max(0.0, float(payload.get("y", 0.5))))
                        page.mouse.click(nx * session.viewport["width"], ny * session.viewport["height"])
                    elif action == "scroll":
                        dy = int(payload.get("dy", 600))
                        page.mouse.wheel(0, dy)
                    with self._lock:
                        session.current_url = page.url
                        session.title = page.title()
                        session.updated_at = time.time()
                except queue.Empty:
                    pass
                except Exception as exc:
                    with self._lock:
                        session.last_error = f"{type(exc).__name__}: {exc}"
                        session.findings.append({"kind": "browser_action_error", "detail": session.last_error[:1200], "severity": "error"})
                        session.updated_at = time.time()

                if now - last_capture >= 0.7:
                    try:
                        frame = page.screenshot(type="png")
                        with self._lock:
                            session.frame = frame
                            session.current_url = page.url
                            session.title = page.title()
                            session.updated_at = time.time()
                    except Exception as exc:
                        with self._lock:
                            session.last_error = f"{type(exc).__name__}: {exc}"
                    last_capture = now
                if now - last_text >= 2.0:
                    try:
                        text = page.locator("body").inner_text(timeout=min(self.timeout_ms, 3000))[:12000]
                        with self._lock:
                            session.visible_text = text
                    except Exception:
                        pass
                    last_text = now
        except Exception as exc:
            with self._lock:
                session.state = "ERROR"
                session.last_error = f"{type(exc).__name__}: {exc}"
                session.findings.append({"kind": "browser_runtime_error", "detail": session.last_error[:1200], "severity": "critical"})
                session.updated_at = time.time()
        finally:
            for obj in (context, browser):
                try:
                    if obj:
                        obj.close()
                except Exception:
                    pass
            try:
                if playwright_cm:
                    playwright_cm.stop()
            except Exception:
                pass
            with self._lock:
                if session.state != "ERROR":
                    session.state = "STOPPED"
                session.stopped = True
                session.paused = False
                session.owner_control = False
                session.updated_at = time.time()
