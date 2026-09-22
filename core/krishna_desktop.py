from __future__ import annotations

"""KRISHNA Windows desktop shell.

The desktop executable is intentionally only a host for the canonical KRISHNA web UI.
It must never carry a second/legacy desktop design. Core behavior and UI contracts stay
identical whether KRISHNA is opened from the browser, desktop EXE, mobile, or CLI.
"""

import sys
import time
import urllib.request
import webbrowser

from krishna_console import CORE_URL, STARTUP_ERRORS, ensure_core

CURRENT_UI_MARKER = 'data-krishna-ui="2026.09-current"'


def _show_error(message: str) -> None:
    text = str(message)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, "KRISHNA", 0x10)
            return
        except Exception:
            pass
    print(text, file=sys.stderr)


def _verify_current_ui(url: str) -> None:
    with urllib.request.urlopen(url, timeout=8) as response:
        html = response.read(512_000).decode("utf-8", errors="replace")
    if CURRENT_UI_MARKER not in html:
        raise RuntimeError(
            "KRISHNA Core is online but is not serving the current desktop design. "
            "Run the verified deployment before opening KRISHNA."
        )


def _browser_fallback(url: str) -> None:
    webbrowser.open(url, new=1)
    # ensure_core() may have started the Core in this process. Keep this host alive
    # so the browser session does not lose its local backend when pywebview is absent.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        return


def main() -> None:
    if not ensure_core():
        detail = "\n".join(STARTUP_ERRORS[-8:]) or "Unknown Core startup error"
        _show_error("KRISHNA Core could not start.\n\n" + detail)
        raise SystemExit(1)

    url = CORE_URL.rstrip("/") + "/"
    try:
        _verify_current_ui(url)
    except Exception as exc:
        _show_error(f"KRISHNA UI verification failed.\n\n{type(exc).__name__}: {exc}")
        raise SystemExit(2)

    try:
        import webview  # type: ignore
    except ImportError:
        _browser_fallback(url)
        return

    # Edge/WebView2 is used by pywebview on current Windows installations. The web
    # surface is the same canonical UI served by Core; there is no second Tkinter UI.
    window = webview.create_window(
        "KRISHNA",
        url=url,
        width=1440,
        height=900,
        min_size=(960, 640),
        text_select=True,
    )
    if window is None:
        raise RuntimeError("KRISHNA desktop window could not be created")
    webview.start(debug=False)


if __name__ == "__main__":
    main()
