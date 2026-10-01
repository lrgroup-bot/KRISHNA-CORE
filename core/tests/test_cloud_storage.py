import unittest
from krishna_core.cloud_storage import StorageProvider,NoFreeCapacity,ZERO_SPEND_POLICY,route,replication_plan,upload_policy
class CloudStorageTests(unittest.TestCase):
 def test_paid_and_account_creation_are_hard_blocked(self):
  self.assertFalse(ZERO_SPEND_POLICY["paid_storage"]);self.assertFalse(ZERO_SPEND_POLICY["auto_upgrade"]);self.assertFalse(ZERO_SPEND_POLICY["auto_account_creation"])
 def test_router_uses_only_authorized_healthy_free_capacity(self):
  ps=[StorageProvider("paid","s3",10**12,free_tier=False),StorageProvider("full","google",1),StorageProvider("g1","google",1000)]
  self.assertEqual(route(ps,100).provider_id,"g1")
 def test_no_capacity_fails_closed_instead_of_buying(self):
  with self.assertRaises(NoFreeCapacity):route([StorageProvider("g1","google",10)],100)
 def test_replication_requires_real_free_capacity(self):
  ps=[StorageProvider("g1","google",1000),StorageProvider("g2","google",900)]
  self.assertEqual(len(replication_plan(ps,100,2)),2)
 def test_mobile_guards(self):
  self.assertFalse(upload_policy(privacy="private",network="cellular",battery_percent=80,size_bytes=200*1024*1024,mobile=True)["upload"])
  self.assertFalse(upload_policy(privacy="never_upload",network="wifi",battery_percent=100,size_bytes=1,mobile=True)["upload"])
  self.assertTrue(upload_policy(privacy="sensitive",network="wifi",battery_percent=80,size_bytes=200*1024*1024,mobile=True)["encrypt"])
if __name__=="__main__":unittest.main()
