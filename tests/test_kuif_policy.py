import unittest

from kuif.policy import PROJECTS, authorize, require_authorized


class KuifPolicyTests(unittest.TestCase):
    def test_registered_projects_are_read_only(self):
        self.assertEqual(len(PROJECTS), 7)
        for project in PROJECTS:
            self.assertTrue(authorize(project, "read"))
            self.assertFalse(authorize(project, "write", approved=True))

    def test_unknown_project_is_denied(self):
        self.assertFalse(authorize("unknown", "read"))
        with self.assertRaises(PermissionError):
            require_authorized("unknown", "read")


if __name__ == "__main__":
    unittest.main()
