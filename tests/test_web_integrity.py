from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"core"/"web_validation.html"

class WebIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text=WEB.read_text(encoding="utf-8")

    def test_single_required_ids(self):
        for element_id in ("home","sudarshan","projects","kabach","garuda","gyan","narad","plugins","specialists","development","work","activity","system","messages","project"):
            needle=f'id="{element_id}"'
            self.assertEqual(self.text.count(needle),1,needle)

    def test_no_literal_escape_artifacts(self):
        self.assertNotIn("showView(\\'",self.text)
        self.assertNotIn("</section>\\n<section",self.text)

    def test_sudarshan_has_complete_spatial_deck(self):
        start=self.text.index('<section id="sudarshan"')
        end=self.text.index('<section id="projects"',start)
        block=self.text[start:end]
        self.assertIn('holoRail left',block)
        self.assertIn('sudarshanCenter',block)
        self.assertIn('holoRail right',block)
        self.assertEqual(block.count("</aside>"),2)
        self.assertIn('id="messages"',block)

    def test_referenced_dom_ids_exist(self):
        ids=set(re.findall(r'id="([^"]+)"',self.text))
        refs=set(re.findall(r"\$\('([^']+)'\)",self.text))
        missing=sorted(refs-ids)
        self.assertEqual(missing,[],missing)

    def test_external_scripts_never_contain_ignored_inline_code(self):
        for attrs,body in re.findall(r"<script\b([^>]*)>([\s\S]*?)</script>",self.text,flags=re.I):
            if re.search(r"\bsrc\s*=",attrs,re.I):
                self.assertFalse(body.strip(),f"inline JavaScript would be ignored for src script: {attrs}")

    def test_inline_javascript_parses_when_node_is_available(self):
        node=shutil.which("node")
        if not node:self.skipTest("node is unavailable")
        scripts=[body for attrs,body in re.findall(r"<script\b([^>]*)>([\s\S]*?)</script>",self.text,flags=re.I)
                 if not re.search(r"\bsrc\s*=",attrs,re.I)
                 and not re.search(r'\btype\s*=\s*["\']importmap["\']',attrs,re.I)
                 and body.strip()]
        self.assertTrue(scripts)
        with tempfile.TemporaryDirectory() as td:
            for i,body in enumerate(scripts):
                path=Path(td)/f"inline-{i}.js";path.write_text(body,encoding="utf-8")
                p=subprocess.run([node,"--check",str(path)],capture_output=True,text=True)
                self.assertEqual(p.returncode,0,(p.stderr or p.stdout)[-4000:])

    def test_no_known_undefined_escape_helper(self):
        self.assertNotRegex(self.text,r"(?<![A-Za-z])esc\(")

    def test_attachment_control_present(self):
        self.assertIn('id="attachInput"',self.text)
        self.assertIn('uploadAttachment(this)',self.text)

    def test_project_create_entry_and_local_avatar_engine_hooks(self):
        self.assertIn('title="Create project"',self.text)
        self.assertIn('onclick="openNewProjectWizard()"',self.text)
        self.assertIn('id="krishnaLiveAvatar"',self.text)
        self.assertIn('"talkinghead":"/assets/avatar-engine/talkinghead/talkinghead.mjs"',self.text)
        self.assertIn('src="/assets/avatar-engine/model-viewer/model-viewer.min.js"',self.text)
        self.assertNotIn('ajax.googleapis.com/ajax/libs/model-viewer',self.text)


if __name__=="__main__":
    unittest.main()
