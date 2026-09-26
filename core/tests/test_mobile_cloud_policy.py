import unittest

from krishna_core.mobile_cloud_policy import MobileCloudPolicy


class MobileCloudPolicyTests(unittest.TestCase):
    def test_general_question_is_mobile_cloud_eligible(self):
        out=MobileCloudPolicy.classify("Explain why the sky looks blue")
        self.assertTrue(out["eligible"])

    def test_private_or_action_requests_escalate_to_pc(self):
        for text in (
            "Fix my KRISHNA project",
            "Open my file and edit it",
            "Pay the supplier",
            "What did I say last time?",
            "Tell me today's Gita verse",
            "My API key is abc",
        ):
            with self.subTest(text=text):
                self.assertFalse(MobileCloudPolicy.classify(text)["eligible"])

    def test_attachments_escalate_to_pc(self):
        self.assertFalse(MobileCloudPolicy.classify("What is this?",attachments=1)["eligible"])


if __name__=="__main__":
    unittest.main()
