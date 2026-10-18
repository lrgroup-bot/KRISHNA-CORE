"""Read completed local MiroFish simulations via its documented Flask API.

No simulation is started here; reports are hypotheses, not predictions verified
by real-world outcomes.
"""
from hashlib import sha256
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from .sudarshan_execution_contract import AdapterResult


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PermissionError('redirects from local simulation API blocked')


def _local_get(url, timeout):
    return build_opener(_NoRedirect()).open(Request(url, method='GET'), timeout=timeout)


def inspect_completed_simulation(simulation_id, project_id, *, authorized=False,
                                 base_url='http://127.0.0.1:5001', transport=None):
    if not authorized:
        raise PermissionError('explicit local simulation read approval required')
    parsed = urlsplit(base_url)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
            or parsed.username or parsed.password or parsed.path not in ('', '/')):
        raise PermissionError('MiroFish API must be on loopback')
    if not isinstance(simulation_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',simulation_id):
        raise ValueError('invalid simulation id')
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError('project id required')
    host = base_url.rstrip('/')
    def get(path):
        with (transport or _local_get)(host + path, timeout=15) as response:
            payload = response.read(2_000_000)
            final = urlsplit(response.geturl())
        if final.hostname not in ('127.0.0.1', 'localhost', '::1') or final.scheme != 'http':
            raise PermissionError('external API redirect denied')
        data = json.loads(payload)
        if not isinstance(data, dict) or data.get('success') is not True:
            raise ValueError('MiroFish API did not confirm success')
        return data.get('data')
    try:
        simulation = get('/api/simulation/' + simulation_id)
        if not isinstance(simulation, dict):
            raise ValueError('invalid simulation')
        if simulation.get('simulation_id') != simulation_id or simulation.get('project_id') != project_id:
            raise PermissionError('simulation project scope mismatch')
        if simulation.get('status') not in ('completed', 'COMPLETED'):
            return AdapterResult('MiroFish', 'not_tested', '', 'simulation not completed')
        report = get('/api/report/by-simulation/' + simulation_id)
        if not isinstance(report, dict) or not report.get('report_id'):
            raise ValueError('completed report missing')
        if report.get('simulation_id') not in (None, simulation_id):
            raise PermissionError('report simulation mismatch')
        if report.get('status') not in ('completed', 'COMPLETED'):
            return AdapterResult('MiroFish', 'not_tested', '', 'report not completed')
    except PermissionError:
        raise
    except (OSError, TimeoutError):
        return AdapterResult('MiroFish', 'blocked', '', 'local MiroFish API unavailable')
    canonical=json.dumps({'simulation':simulation,'report':report},sort_keys=True).encode()
    return AdapterResult('MiroFish', 'passed', 'sha256:' + sha256(canonical).hexdigest(),
                         'completed local simulation report collected; hypothesis only')
