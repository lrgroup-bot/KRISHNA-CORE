import unittest
from garuda_engine import Device, Job, Status, Worker, can_admit, diagnostic_plan, select_worker


class GarudaEngineTests(unittest.TestCase):
    def test_no_selection_no_test(self):
        self.assertEqual(diagnostic_plan(Device("a", "storage", "usb", admin_approved=True)).status, Status.BLOCKED)

    def test_critical_drive_is_protected(self):
        plan = diagnostic_plan(Device("hdd", "storage", "usb", selected=True, admin_approved=True, clicking=True))
        self.assertEqual(plan.profile, "RECOVERY_PROTECT")
        self.assertNotIn("read_only_scan_if_safe", plan.checks)

    def test_remote_computer_needs_enrollment(self):
        self.assertEqual(diagnostic_plan(Device("pc", "computer", "lan", selected=True, admin_approved=True)).status, Status.BLOCKED)

    def test_full_pro_is_plan_not_fake_pass(self):
        plan = diagnostic_plan(Device("sw", "switch", "lan", selected=True, admin_approved=True))
        self.assertEqual(plan.profile, "FULL_PRO")
        self.assertEqual(plan.status, Status.NOT_TESTED)

    def test_hot_or_busy_node_rejected(self):
        hot = Worker("hot", True, True, 40, .1, 256, 50, temperature_c=96, max_safe_temperature_c=90)
        busy = Worker("busy", True, True, 40, .9, 256, 50)
        self.assertFalse(can_admit(hot, Job("j", 2, 8)))
        self.assertFalse(can_admit(busy, Job("j", 2, 8)))

    def test_capacity_and_deterministic_selection(self):
        a = Worker("a", True, True, 40, .6, 256, 100)
        b = Worker("b", True, True, 80, .2, 256, 100, 24, 5)
        job = Job("qwen", 4, 12, 8)
        self.assertEqual(select_worker([a, b], job), "b")
        self.assertIsNone(select_worker([a], job))


if __name__ == "__main__":
    unittest.main()
