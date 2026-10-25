"""Native SURYADEV-only HTTPS bind validation; no sockets opened in CI."""
import tempfile
from pathlib import Path
import unittest

from krishna_core.suryadev_tls_runtime import (
    allowed_method_path, checked_private_bind, tls_settings,
)


class NativeTLSTests(unittest.TestCase):
    def test_disabled_by_default_and_partial_configuration_refused(self):
        self.assertIsNone(tls_settings({}))
        with self.assertRaises(ValueError):
            tls_settings({"KRISHNA_SURYADEV_TLS_CERT_FILE":"cert.pem"})

    def test_specific_private_ip_required(self):
        for host in ("0.0.0.0","8.8.8.8","public.example.com","::",
                     "2001:4860:4860::8888"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                checked_private_bind(host)
        self.assertEqual(checked_private_bind("192.168.0.100"),"192.168.0.100")
        self.assertEqual(checked_private_bind("127.0.0.1"),"127.0.0.1")

    def test_route_surface_restricted_even_for_paired_device(self):
        self.assertTrue(allowed_method_path("POST","/api/mobile/pair/request"))
        self.assertTrue(allowed_method_path("POST","/api/suryadev/fleet/complete"))
        self.assertTrue(allowed_method_path("GET","/api/suryadev/device/status"))
        for method,route in (("POST","/api/mobile/pair/approve"),
                             ("GET","/api/mobile/pair/pending"),
                             ("GET","/api/suryadev/fleet/status"),
                             ("GET","/api/core/state"),
                             ("POST","/api/core/chat"),
                             ("POST","/api/suryadev/fleet/status"),
                             ("GET","/api/mobile/pair/request")):
            with self.subTest(method=method,route=route):
                self.assertFalse(allowed_method_path(method,route))

    def test_valid_config_requires_concrete_certificate_and_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            cert=Path(tmp)/"cert.pem";key=Path(tmp)/"key.pem"
            cert.write_text("test-placeholder");key.write_text("test-placeholder")
            bind,port,first,second=tls_settings({
                "KRISHNA_SURYADEV_TLS_CERT_FILE":str(cert),
                "KRISHNA_SURYADEV_TLS_KEY_FILE":str(key),
                "KRISHNA_SURYADEV_TLS_BIND_IP":"192.168.0.100",
                "KRISHNA_SURYADEV_TLS_PORT":"8443"})
            self.assertEqual((bind,port),("192.168.0.100",8443))
            # Windows CI may render the same temp directory as RUNNER~1
            # or its expanded long path; compare file identities.
            self.assertTrue(first.samefile(cert))
            self.assertTrue(second.samefile(key))


if __name__=="__main__":
    unittest.main()
