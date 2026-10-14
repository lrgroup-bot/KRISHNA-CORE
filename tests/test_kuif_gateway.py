import unittest

from kuif.gateway import DEFAULT_ENDPOINT, ModelEndpoint, validate_endpoint


class KuifGatewayTests(unittest.TestCase):
    def test_default_endpoint(self):
        validate_endpoint(DEFAULT_ENDPOINT)

    def test_reject_unsafe_endpoints(self):
        urls = [
            "https://example.com:11434",
            "http://192.168.1.10:11434",
            "http://localhost:8000",
            "http://user:pass@localhost:11434",
            "http://localhost:abc",
            "http://localhost:11434/evil",
            "http://localhost:11434/?redirect=1",
        ]
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_endpoint(ModelEndpoint("unsafe", url))

    def test_cloud_disabled(self):
        with self.assertRaises(ValueError):
            validate_endpoint(ModelEndpoint("cloud", "http://localhost:11434", "cloud"))


if __name__ == "__main__":
    unittest.main()
