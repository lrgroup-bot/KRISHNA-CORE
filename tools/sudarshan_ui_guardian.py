"""Real Playwright-driven browser smoke tests for UI Guardian.

Only owner-approved URLs and declarative browser actions are supported. Mobile
mode is a responsive browser emulation, *not* a native Android/iOS device test.
Requires playwright and an installed Chromium browser on the host machine.
"""
import hashlib
import json
from urllib.parse import urlsplit
from .sudarshan_execution_contract import AdapterResult

ACTIONS = frozenset({'click', 'fill', 'expect_text', 'expect_visible'})


def _host_allowed(url, hosts):
    parsed = urlsplit(url)
    return parsed.scheme in ('http', 'https') and parsed.hostname in hosts and not parsed.username and not parsed.password


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise TypeError('browser plan must be a dictionary')
    hosts = plan.get('allow_hosts', ['localhost', '127.0.0.1'])
    if not isinstance(hosts, list) or not hosts or any(not isinstance(x, str) or not x for x in hosts):
        raise ValueError('explicit nonempty allowed hosts required')
    hosts = frozenset(hosts)
    if not isinstance(plan.get('url'), str) or not _host_allowed(plan['url'], hosts):
        raise PermissionError('target URL not in allowed host set')
    if plan.get('device', 'desktop') not in ('desktop', 'mobile_emulation'):
        raise ValueError('unknown browser device mode')
    steps = plan.get('steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError('at least one UI test step required')
    for step in steps:
        if (not isinstance(step, dict) or step.get('action') not in ACTIONS or
                not isinstance(step.get('selector'), str) or not step['selector'].strip()):
            raise ValueError('unsupported action or missing selector')
        if step['action'] in ('fill', 'expect_text') and not isinstance(step.get('value'), str):
            raise ValueError('fill/expect_text requires string value')
    return hosts


def run_browser(plan, *, authorized=False):
    """Drive real Chromium via Playwright; return actual test evidence, not fixtures."""
    if not authorized:
        raise PermissionError('explicit UI test approval required')
    hosts = validate_plan(plan)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return AdapterResult('UI_GUARDIAN', 'blocked', '', 'playwright unavailable')
    completed = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                mobile = plan.get('device') == 'mobile_emulation'
                ctx = browser.new_context(viewport={'width': 390 if mobile else 1280,
                                                     'height': 844 if mobile else 800},
                                          is_mobile=mobile, has_touch=mobile)
                try:
                    # Block third-party navigations and asset requests by default.
                    ctx.route('**/*', lambda route: route.continue_() if
                              (_host_allowed(route.request.url, hosts) or
                               route.request.url.startswith(('data:', 'about:'))) else route.abort())
                    page = ctx.new_page()
                    page.goto(plan['url'], wait_until='domcontentloaded', timeout=15000)
                    for step in plan['steps']:
                        locator = page.locator(step['selector'])
                        action = step['action']
                        if action == 'click':
                            locator.click(timeout=8000)
                        elif action == 'fill':
                            locator.fill(step['value'], timeout=8000)
                        elif action == 'expect_visible':
                            locator.wait_for(state='visible', timeout=8000)
                        elif action == 'expect_text':
                            locator.wait_for(state='visible', timeout=8000)
                            if step['value'] not in locator.inner_text(timeout=8000):
                                raise AssertionError('expected text mismatch')
                        completed.append({'action': action, 'selector': step['selector']})
                finally:
                    ctx.close()
            finally:
                browser.close()
    except Exception as error:
        return AdapterResult('UI_GUARDIAN', 'failed', '',
                             'browser execution failed after %d steps (%s)' %
                             (len(completed), type(error).__name__))
    proof = hashlib.sha256(json.dumps({'url': plan['url'], 'device': plan.get('device', 'desktop'),
                                       'steps': plan['steps'], 'completed': completed},
                                      sort_keys=True).encode()).hexdigest()
    return AdapterResult('UI_GUARDIAN', 'passed', 'sha256:' + proof,
                         '%d actual Chromium UI steps completed' % len(completed))
