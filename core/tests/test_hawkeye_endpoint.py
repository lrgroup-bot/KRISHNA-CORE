import unittest
from krishna_core.hawkeye_endpoint import HawkeyeEndpointPolicy

class HawkeyeEndpointPolicyTests(unittest.TestCase):
    def test_private_pc_precedes_cloud(self):
        p=HawkeyeEndpointPolicy("http://192.168.1.10:8766","https://krishna.example.com")
        self.assertEqual([x.name for x in p.candidates()],["pc-private","cloud-relay"])

    def test_cloud_must_be_https(self):
        p=HawkeyeEndpointPolicy("", "http://krishna.example.com")
        self.assertEqual(p.candidates(),[])

    def test_phone_field_fallback_needs_no_network(self):
        self.assertFalse(HawkeyeEndpointPolicy().field_fallback()["network_required"])

if __name__=="__main__": unittest.main()
