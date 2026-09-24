import unittest

from krishna_core.remote_access import PrivateRemotePolicy


class PrivateRemoteMobileSyncPolicyTests(unittest.TestCase):
    def test_mobile_bootstrap_and_media_sync_are_allowlisted(self):
        policy=PrivateRemotePolicy("100.64.0.0/10")
        for path in (
            "/api/mobile/bootstrap",
            "/api/hawkeye/media-sync/start",
            "/api/hawkeye/media-sync/chunk",
            "/api/hawkeye/media-sync/complete",
            "/api/hawkeye/media-sync/status",
        ):
            with self.subTest(path=path):
                self.assertTrue(policy.mobile_route_allowed(path))

    def test_public_addresses_remain_rejected(self):
        policy=PrivateRemotePolicy("100.64.0.0/10")
        self.assertTrue(policy.allowed("100.69.70.106"))
        self.assertTrue(policy.allowed("192.168.0.10"))
        self.assertFalse(policy.allowed("8.8.8.8"))


if __name__=="__main__":
    unittest.main()
