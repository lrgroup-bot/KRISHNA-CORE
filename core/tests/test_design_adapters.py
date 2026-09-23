import unittest

from krishna_core.design_adapters import StagehandAdapter, StorybookAdapter


class DesignAdapterTests(unittest.TestCase):
    def test_stagehand_is_opt_in(self):
        self.assertFalse(StagehandAdapter().available())
        self.assertTrue(StagehandAdapter(enabled=True).available())

    def test_storybook_contract_covers_error_and_mobile_states(self):
        states=StorybookAdapter().required_states()
        self.assertIn("error",states)
        self.assertIn("mobile",states)


if __name__=="__main__":
    unittest.main()
