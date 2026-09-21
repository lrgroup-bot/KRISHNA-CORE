import tempfile
import unittest
from pathlib import Path
from krishna_core.garudanetra_session import GarudanetraSessionManager

class GarudanetraSessionTests(unittest.TestCase):
    def test_url_validation(self):
        self.assertEqual(GarudanetraSessionManager.validate_url("https://example.com"),"https://example.com")
        for value in ("","file:///tmp/x","javascript:alert(1)","example.com"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                GarudanetraSessionManager.validate_url(value)

    def test_empty_manager_status(self):
        with tempfile.TemporaryDirectory() as td:
            m=GarudanetraSessionManager(Path(td))
            self.assertEqual(m.status()["count"],0)
            with self.assertRaises(KeyError): m.status("missing")

    def test_unknown_action_is_rejected_without_browser_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            m=GarudanetraSessionManager(Path(td))
            # construct a session record without starting Playwright so this contract is environment independent
            from krishna_core.garudanetra_session import BrowserSession
            s=BrowserSession("s","KRISHNA","https://example.com")
            m._sessions["s"]=s
            import queue
            m._commands["s"]=queue.Queue()
            with self.assertRaises(ValueError): m.command("s","arbitrary_shell",{})

if __name__=="__main__": unittest.main()
