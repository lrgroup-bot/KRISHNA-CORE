import base64
import unittest
from email import message_from_bytes
from unittest.mock import patch

from krishna_core.narad.providers import NaradProviderHub


class NaradGmailThreadingTests(unittest.TestCase):
    def test_gmail_sales_reply_preserves_thread_and_reply_headers(self):
        seen={}
        def fake_request(url,method="POST",body=None,headers=None,timeout=45):
            seen.update({"url":url,"method":method,"body":body,"headers":headers})
            return {"status":200,"ok":True,"data":{"id":"m2","threadId":"thread-1"}}

        hub=NaradProviderHub()
        with patch("krishna_core.narad.providers._json_request",side_effect=fake_request):
            out=hub.send(
                "gmail","send_email",
                {
                    "to":"buyer@example.com",
                    "subject":"Re: CRM proposal",
                    "text":"Here is the requested quotation.",
                    "thread_id":"thread-1",
                    "in_reply_to":"<message-1@example.com>",
                    "references":"<message-1@example.com>",
                },
                {"Authorization":"Bearer test-token"},
            )
        self.assertTrue(out["ok"])
        self.assertEqual(seen["body"]["threadId"],"thread-1")
        raw=seen["body"]["raw"]
        raw += "=" * (-len(raw) % 4)
        msg=message_from_bytes(base64.urlsafe_b64decode(raw.encode("ascii")))
        self.assertEqual(msg["In-Reply-To"],"<message-1@example.com>")
        self.assertEqual(msg["References"],"<message-1@example.com>")
        self.assertIn("Here is the requested quotation.",msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8"))


if __name__=="__main__":
    unittest.main()
