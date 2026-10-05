from pathlib import Path
import tempfile
import unittest

from core.architecture_intelligence import ArchifyPolicy, archify_environment


class ArchitectureIntelligencePolicyTests(unittest.TestCase):
    def test_update_check_is_forced_off(self):
        self.assertEqual(archify_environment({})["ARCHIFY_UPDATE_CHECK_DISABLED"], "1")

    def test_privileged_actions_fail_closed(self):
        policy = ArchifyPolicy()
        for action in ("repo-write", "merge", "deploy", "spend", "approve"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionError):
                    policy.assert_no_privileged_action(action)

    def test_output_cannot_be_repo_root_or_protected_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            (repo / "core").mkdir(parents=True)
            policy = ArchifyPolicy()
            with self.assertRaises(ValueError):
                policy.assert_safe_paths(repo, repo)
            with self.assertRaises(ValueError):
                policy.assert_safe_paths(repo, repo / "core" / "archify")

    def test_dedicated_generated_output_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            out = root / "generated-architecture"
            policy = ArchifyPolicy()
            policy.assert_safe_paths(repo, out)


if __name__ == "__main__":
    unittest.main()
