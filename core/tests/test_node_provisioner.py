import unittest
from krishna_core.node_provisioner import NodeProvisioner,Capacity
class T(unittest.TestCase):
 def test_power_profile_and_fallback(self):
  p=NodeProvisioner(); a={"id":"vision-large","profiles":["power"],"source":"https://example.invalid/model","sha256":"abc"}; plan=p.provision_plan(Capacity(64,24,16,200),[a],True); self.assertEqual(plan["profile"],"power"); self.assertEqual(p.next_method(plan["artifacts"][0],False),"DOWNLOAD_VERIFY_INSTALL")
 def test_weak_node_skips_power_asset(self):
  p=NodeProvisioner(); plan=p.provision_plan(Capacity(8,0,4,20),[{"id":"big","profiles":["power"]}],True); self.assertEqual(plan["artifacts"],[])
