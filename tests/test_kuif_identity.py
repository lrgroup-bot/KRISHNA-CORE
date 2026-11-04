"""Identity and project-scoping tests discovered by unittest CI."""
import unittest
from kuif.identity import Principal, can_access


class IdentityTests(unittest.TestCase):
    def test_scoped_principal(self):
        user = Principal("user-1", frozenset({"krishna"}), frozenset({"read"}))
        self.assertTrue(can_access(user, "krishna", "read"))
        self.assertFalse(can_access(user, "kuber", "read"))
        self.assertFalse(can_access(user, "krishna", "analyze"))
        self.assertFalse(can_access(user, "krishna", "write"))

    def test_anonymous_denied(self):
        self.assertFalse(can_access(
            Principal("", frozenset({"krishna"}), frozenset({"read"})),
            "krishna", "read",
        ))


if __name__ == "__main__":
    unittest.main()
