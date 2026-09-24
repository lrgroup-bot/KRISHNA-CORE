from __future__ import annotations

from http.server import ThreadingHTTPServer


class KrishnaThreadingHTTPServer(ThreadingHTTPServer):
    """KRISHNA HTTP server tuned for bursty local UI/API traffic on Windows.

    The default socket backlog inherited by HTTPServer can be too small for the
    dashboard's first-load burst of parallel API requests. A larger backlog keeps
    those legitimate loopback/Tailscale connections queued instead of refused.

    daemon_threads also prevents short-lived request handlers from blocking clean
    shutdown during acceptance tests and supervised restarts.
    """

    request_queue_size = 128
    daemon_threads = True
    allow_reuse_address = True
