import unittest

from kuif.health import tcp_reachable


class KuifHealthTests(unittest.TestCase):
    def test_nonlocal_rejected(self):
        with self.assertRaises(ValueError):
            tcp_reachable("example.com")

    def test_invalid_port_rejected(self):
        with self.assertRaises(ValueError):
            tcp_reachable(port=0)


if __name__ == "__main__":
    unittest.main()
