import tempfile
import unittest
from pathlib import Path

from krishna_core.narad.messages import NaradMessageStore


class NaradMessageStoreTests(unittest.TestCase):
    def test_inbox_and_outbox_are_durable(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"messages.json"
            store=NaradMessageStore(path)
            incoming=store.add(direction="inbox",provider="whatsapp",text="hello",sender="contact")
            draft=store.add(direction="outbox",provider="whatsapp",text="reply",recipients=["contact"])
            self.assertEqual(incoming["state"],"received")
            self.assertEqual(draft["state"],"draft")
            again=NaradMessageStore(path)
            self.assertEqual(again.status()["count"],2)

    def test_message_secrets_are_redacted(self):
        with tempfile.TemporaryDirectory() as td:
            store=NaradMessageStore(Path(td)/"messages.json")
            row=store.add(direction="inbox",provider="gmail",text="password: abc123secret")
            self.assertNotIn("abc123secret",row["text"])
            self.assertIn("[REDACTED]",row["text"])

    def test_inbox_cannot_be_marked_sent(self):
        with tempfile.TemporaryDirectory() as td:
            store=NaradMessageStore(Path(td)/"messages.json")
            row=store.add(direction="inbox",provider="slack",text="x")
            with self.assertRaises(ValueError):
                store.transition(row["id"],"sent")

    def test_outbox_transition_records_provider_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            store=NaradMessageStore(Path(td)/"messages.json")
            row=store.add(direction="outbox",provider="telegram",text="x")
            sent=store.transition(row["id"],"sent",provider_receipt={"id":"provider-1"})
            self.assertEqual(sent["state"],"sent")
            self.assertEqual(sent["provider_receipt"]["id"],"provider-1")


if __name__=="__main__":
    unittest.main()
