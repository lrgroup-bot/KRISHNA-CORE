"""UI Guardian: Playwright Chromium functional assertions with real-state evidence.

No arbitrary Python/JS expression or unapproved external navigation. Service
workers are disabled so network routing cannot be bypassed by SW fetches.
Mobile emulation remains distinct from physical Android ADB inspection.
"""
import base64
import hashlib
import json
from urllib.parse import urlsplit

from .sudarshan_execution_contract import AdapterResult
from .sudarshan_evidence_archive import archive

ACTIONS = frozenset({'click','fill','expect_text','expect_visible','expect_count'})


def _host_allowed(url, hosts):
    parsed = urlsplit(url)
    return (parsed.scheme in ('http','https') and parsed.hostname in hosts and
            not parsed.username and not parsed.password)


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise TypeError('browser plan must be a dictionary')
    hosts = plan.get('allow_hosts', ['localhost','127.0.0.1'])
    if not isinstance(hosts, list) or not hosts or any(
            not isinstance(x,str) or not x or len(x)>255 for x in hosts):
        raise ValueError('explicit bounded allowed hosts required')
    hosts=frozenset(hosts)
    if not isinstance(plan.get('url'),str) or not _host_allowed(plan['url'],hosts):
        raise PermissionError('target URL not in allowed host set')
    if plan.get('device','desktop') not in ('desktop','mobile_emulation'):
        raise ValueError('unknown browser device mode')
    if type(plan.get('fail_on_console_error',True)) is not bool:
        raise ValueError('fail_on_console_error must be boolean')
    steps=plan.get('steps')
    if not isinstance(steps,list) or not 1<=len(steps)<=100:
        raise ValueError('1..100 UI steps required')
    for step in steps:
        if (not isinstance(step,dict) or step.get('action') not in ACTIONS or
                not isinstance(step.get('selector'),str) or
                not 1<=len(step['selector'].strip())<=300):
            raise ValueError('unsupported action or missing/long selector')
        if step['action'] in ('fill','expect_text') and not isinstance(step.get('value'),str):
            raise ValueError('fill/expect_text requires string value')
        if step['action']=='expect_count' and (type(step.get('value')) is not int or
                                                not 0<=step['value']<=10000):
            raise ValueError('expect_count requires bounded integer value')
    return hosts


def run_browser(plan, *, authorized=False, evidence_root=None, project_id=None):
    """Actually execute Chromium assertions and hash captured browser state."""
    if not authorized:
        raise PermissionError('explicit UI test approval required')
    hosts=validate_plan(plan)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return AdapterResult('UI_GUARDIAN','blocked','','playwright unavailable')

    completed=[]
    console_errors=[]
    response_failures=[]
    screenshot=b''
    final_url=''
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            try:
                mobile=plan.get('device')=='mobile_emulation'
                ctx=browser.new_context(
                    viewport={'width':390 if mobile else 1280,
                              'height':844 if mobile else 800},
                    is_mobile=mobile, has_touch=mobile, service_workers='block')
                try:
                    ctx.route('**/*',lambda route:
                        route.continue_() if (_host_allowed(route.request.url,hosts) or
                        route.request.url.startswith(('data:','about:'))) else route.abort())
                    page=ctx.new_page()
                    page.on('console',lambda item:
                        console_errors.append(item.type) if item.type=='error' else None)
                    page.on('pageerror',lambda error:console_errors.append('pageerror'))
                    page.on('requestfailed',lambda request:
                        response_failures.append(request.url[:400]))
                    page.goto(plan['url'],wait_until='domcontentloaded',timeout=15000)
                    for step in plan['steps']:
                        action=step['action']
                        locator=page.locator(step['selector'])
                        if action=='click':
                            locator.click(timeout=8000)
                        elif action=='fill':
                            locator.fill(step['value'],timeout=8000)
                        elif action=='expect_visible':
                            locator.wait_for(state='visible',timeout=8000)
                        elif action=='expect_text':
                            locator.wait_for(state='visible',timeout=8000)
                            if step['value'] not in locator.inner_text(timeout=8000):
                                raise AssertionError('expected text mismatch')
                        elif action=='expect_count':
                            if locator.count()!=step['value']:
                                raise AssertionError('expected element count mismatch')
                        if not _host_allowed(page.url,hosts):
                            raise PermissionError('browser navigated to unapproved host')
                        completed.append({'action':action,'selector':step['selector']})
                    final_url=page.url
                    screenshot=page.screenshot(full_page=False,animations='disabled')
                    if len(screenshot)>2_000_000:
                        raise ValueError('Chromium screenshot exceeds bounded evidence size')
                    if plan.get('fail_on_console_error',True) and console_errors:
                        raise AssertionError('Chromium console/page errors detected')
                finally:
                    ctx.close()
            finally:
                browser.close()
    except Exception as error:
        return AdapterResult(
            'UI_GUARDIAN','failed','',
            'Chromium execution failed after %d steps (%s)'%
            (len(completed),type(error).__name__))

    payload={
        'source':'playwright_chromium_real_execution',
        'requested_url':plan['url'],'observed_url':final_url,
        'device_mode':plan.get('device','desktop'),
        'steps':completed, 'step_count':len(completed),
        'screenshot_sha256':hashlib.sha256(screenshot).hexdigest(),
        'console_error_count':len(console_errors),
        'failed_request_count':len(response_failures),
        'service_workers':'block',
        'screenshot_png_base64':base64.b64encode(screenshot).decode('ascii'),
    }
    encoded=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
    evidence_id=(archive(evidence_root,project_id,'UI_GUARDIAN',encoded)
                 if evidence_root is not None else
                 'sha256:'+hashlib.sha256(encoded).hexdigest())
    return AdapterResult('UI_GUARDIAN','passed',evidence_id,
        '%d actual Chromium UI steps completed; %d console errors; %d failed requests' %
        (len(completed),len(console_errors),len(response_failures)))
