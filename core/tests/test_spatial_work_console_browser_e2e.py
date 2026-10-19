"""Real built React controls against controlled HTTP responses; no model calls."""
import json
import mimetypes
import os
from pathlib import Path
import unittest


@unittest.skipUnless(os.getenv('KRISHNA_SPATIAL_UI_E2E') == '1', 'built spatial UI browser E2E disabled')
class SpatialWorkConsoleBrowserTests(unittest.TestCase):
    def test_approval_privacy_receipts_and_plain_text_chat(self):
        from playwright.sync_api import sync_playwright, expect
        root = Path(__file__).resolve().parents[2] / 'app/spatial-ui/dist'
        self.assertTrue((root / 'index.html').is_file(), 'build the spatial frontend first')
        dispatched = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))

                def respond(route):
                    from urllib.parse import urlsplit
                    path = urlsplit(route.request.url).path
                    if not path.startswith('/api/'):
                        asset = path.removeprefix('/spatial/').lstrip('/')
                        file = root / (asset or 'index.html')
                        if not file.resolve().is_relative_to(root.resolve()) or not file.is_file():
                            return route.fulfill(status=404, body='')
                        return route.fulfill(content_type=mimetypes.guess_type(file.name)[0] or 'application/octet-stream', body=file.read_bytes())
                    data = {}
                    if path == '/api/projects':
                        data = {'projects': [{'name': 'PRIVATE_FIXTURE', 'role': 'active', 'privacy': 'local_only', 'verification_checks': ['python-tests']}]}
                    elif path == '/api/core/chat':
                        data = {'text': '<img src=x onerror=alert(1)> is plain text'}
                    elif path == '/api/action-bus/dispatch':
                        payload = route.request.post_data_json
                        self.assertIs(payload['approved'], True)
                        self.assertIs(payload['payload']['approve_build'], True)
                        dispatched.append(payload)
                        data = {'result': {'status': 'verified_candidate', 'tests': {'passed': True}, 'stage_receipts': [{'agent': 'developer', 'action': 'development.verify', 'action_id': 'fixture-receipt'}]}}
                    return route.fulfill(content_type='application/json', body=json.dumps(data))

                page.route('**/*', respond)
                page.goto('http://127.0.0.1:7777/', wait_until='domcontentloaded')
                page.get_by_role('navigation', name='Main Menu').get_by_role('button', name='Sudarshan', exact=True).click()
                work = page.get_by_role('region', name='Sudarshan work console')
                expect(work).to_be_visible()
                work.get_by_label('Message to Krishna', exact=True).fill('hello')
                work.get_by_role('button', name='Send message', exact=True).click()
                expect(work.get_by_label('Conversation', exact=True)).to_contain_text('is plain text')
                self.assertEqual(work.locator('.work-chat img').count(), 0)
                work.get_by_text('Isolated engineering candidate', exact=True).click()
                work.get_by_label('Engineering task', exact=True).fill('repair the fixture')
                run = work.get_by_role('button', name='Run candidate workflow', exact=True)
                expect(run).to_be_disabled()
                self.assertEqual(dispatched, [])
                work.get_by_label('Allow GARUDA', exact=False).check()
                expect(work.get_by_label('Allow a verified zero-cost', exact=False)).to_be_disabled()
                work.get_by_label('Allow GARUDA', exact=False).uncheck()
                work.get_by_label('I approve local model use', exact=False).check()
                run.click()
                expect(work.get_by_label('Workflow outcome', exact=True)).to_contain_text('fixture-receipt')
                self.assertEqual(len(dispatched), 1)
                self.assertFalse(dispatched[0]['payload']['use_free_cloud'])
                self.assertFalse(dispatched[0]['payload']['approved_public_context'])
                expect(work.get_by_label('I approve local model use', exact=False)).not_to_be_checked()
                self.assertEqual(errors, [])
            finally:
                browser.close()
