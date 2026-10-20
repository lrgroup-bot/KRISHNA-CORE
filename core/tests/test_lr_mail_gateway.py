import json
import unittest
from io import BytesIO

from krishna_core.lr_mail_gateway import LRMailGateway
from krishna_core.remote_access import PrivateRemotePolicy


class _Response:
    def __init__(self,payload):
        self.payload=json.dumps(payload).encode("utf-8")
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n=-1):return self.payload if n<0 else self.payload[:n]


class LRMailGatewayTests(unittest.TestCase):
    def test_unconfigured_gateway_is_fail_closed(self):
        gateway=LRMailGateway(base_url="",read_token="")
        self.assertFalse(gateway.status()["configured"])
        self.assertTrue(gateway.status()["read_only"])
        self.assertFalse(gateway.status()["mutations_allowed"])
        with self.assertRaises(RuntimeError):gateway.summary()

    def test_public_cleartext_endpoint_is_rejected(self):
        gateway=LRMailGateway(base_url="http://example.com",read_token="x"*32)
        self.assertFalse(gateway.status()["configured"])
        with self.assertRaises(PermissionError):gateway.summary()

    def test_summary_uses_bounded_get_and_redacts_sensitive_fields(self):
        seen={}
        def opener(request,timeout=0):
            seen["url"]=request.full_url
            seen["auth"]=request.headers.get("Authorization")
            return _Response({"unread":3,"providerTotal":8,"token":"must-not-leak"})
        gateway=LRMailGateway(
            base_url="https://lr.internal.example",
            read_token="r"*32,
            opener=opener,
        )
        result=gateway.summary(999)
        self.assertIn("limit=100",seen["url"])
        self.assertEqual(seen["auth"],"Bearer "+"r"*32)
        self.assertEqual(result["unread"],3)
        self.assertEqual(result["token"],"[REDACTED]")

    def test_list_and_get_are_read_only_contracts(self):
        payloads=[
            {"messages":[{"id":"m1","subject":"Hello"}]},
            {"id":"m1","subject":"Hello","bodyValues":{"1":{"value":"Body"}}},
        ]
        calls=[]
        def opener(request,timeout=0):
            calls.append((request.get_method(),request.full_url))
            return _Response(payloads.pop(0))
        gateway=LRMailGateway(base_url="https://lr.example",read_token="z"*32,opener=opener)
        self.assertEqual(gateway.list(10,0,"hello")["messages"][0]["id"],"m1")
        self.assertEqual(gateway.get("m1")["id"],"m1")
        self.assertTrue(all(method=="GET" for method,_ in calls))

    def test_paired_mobile_policy_allows_only_lr_mail_read_routes(self):
        policy=PrivateRemotePolicy()
        for path in ("/api/lr-mail/status","/api/lr-mail/summary","/api/lr-mail/messages","/api/lr-mail/message"):
            self.assertTrue(policy.mobile_route_allowed(path))
        self.assertFalse(policy.mobile_route_allowed("/api/admin/mail/provision"))
        self.assertFalse(policy.mobile_route_allowed("/api/lr-mail/send"))


if __name__=="__main__":
    unittest.main()
