"""Contract test: Vishvakarma is a bounded agent in the canonical dispatcher."""
from pathlib import Path
import ast
import unittest


class VishvakarmaRegistrationContract(unittest.TestCase):
    def test_registered_with_bounded_actions(self):
        source = Path(__file__).resolve().parents[1] / "krishna_core" / "orchestrator.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        matches = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not isinstance(fn, ast.Attribute) or fn.attr != "register":
                continue
            if not isinstance(fn.value, ast.Attribute) or fn.value.attr != "agent_runtime":
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value != "vishvakarma":
                continue
            matches.append(node)
        self.assertEqual(len(matches), 1, "Vishvakarma must have exactly one agent registration")
        keywords = {k.arg: k.value for k in matches[0].keywords}
        actions = ast.literal_eval(keywords["actions"])
        permissions = ast.literal_eval(keywords["permissions"])
        self.assertIn("vishvakarma.repair.*", actions)
        self.assertIn("vishvakarma.retrieve", actions)
        self.assertNotIn("live.write", permissions)
        self.assertNotIn("send_external", permissions)


if __name__ == "__main__":
    unittest.main()
