"""Bounded loopback-only transport shared by the two existing local routers."""
import ipaddress
import json
import threading
import urllib.request
import urllib.error
from urllib.parse import urlsplit

_SLOTS = threading.BoundedSemaphore(1)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PermissionError('local model redirect blocked')


def validate_local_url(url):
    parsed = urlsplit(str(url))
    try: loopback = ipaddress.ip_address(parsed.hostname or '').is_loopback
    except ValueError: loopback = parsed.hostname == 'localhost'
    if parsed.scheme not in {'http', 'https'} or not loopback or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PermissionError('local model transport requires a credential-free loopback URL')
    return str(url)


def request_local_json(url, payload, timeout=90):
    validate_local_url(url)
    raw = json.dumps(payload).encode('utf-8')
    if len(raw) > 256 * 1024: raise ValueError('local model request exceeds the bounded context budget')
    slots = _SLOTS
    if not slots.acquire(timeout=2): raise RuntimeError('local model busy; request not queued')
    try:
        request = urllib.request.Request(url, data=raw, headers={'Content-Type':'application/json'})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(request, timeout=max(1, min(90, int(timeout)))) as response:
                data = response.read(2 * 1024 * 1024 + 1)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f'local model HTTP {exc.code}; details withheld') from None
        except urllib.error.URLError:
            raise RuntimeError('local model transport unavailable') from None
        if len(data) > 2 * 1024 * 1024: raise ValueError('local model response exceeds limit')
        result = json.loads(data.decode('utf-8'))
        if not isinstance(result, dict): raise ValueError('local model returned invalid shape')
        return result
    finally:
        slots.release()
