"""KRISHNA browser fabric must never launch branded Google Chrome or Edge."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]/"krishna_core"


def browser_launch_calls(filename):
    tree=ast.parse((ROOT/filename).read_text(encoding="utf-8"))
    matches=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Call):
            continue
        func=node.func
        if not (isinstance(func,ast.Attribute) and
                func.attr in ("launch","launch_persistent_context")):
            continue
        obj=func.value
        if not (isinstance(obj,ast.Attribute) and obj.attr=="chromium"):
            continue
        matches.append(node)
    return matches


class OneGarudanetraEngineContract(unittest.TestCase):
    def test_core_inspector_and_sessions_only_use_owned_chromium_channel(self):
        for filename in ("browser_operator.py","garudanetra_session.py"):
            with self.subTest(filename=filename):
                calls=browser_launch_calls(filename)
                self.assertGreaterEqual(len(calls),2)
                for call in calls:
                    kwargs={x.arg:x.value for x in call.keywords if x.arg}
                    self.assertIn("channel",kwargs)
                    self.assertIsInstance(kwargs["channel"],ast.Constant)
                    self.assertEqual(kwargs["channel"].value,"chromium")
        self.assertNotIn('channel="chrome"',
            (ROOT/"browser_operator.py").read_text())
        self.assertNotIn('channel="chrome"',
            (ROOT/"garudanetra_session.py").read_text())


if __name__=="__main__":
    unittest.main()
