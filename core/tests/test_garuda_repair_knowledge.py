import tempfile
import unittest
from krishna_core.garuda_repair_knowledge import RepairKnowledgeStore
class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=RepairKnowledgeStore(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_catalog_dedup(self):
        record={"manufacturer":"Acme","model":"Laptop 1","device_kind":"laptop"}
        self.assertEqual(self.store.add("devices",record)["id"],self.store.add("devices",record)["id"])
        self.assertEqual(len(self.store.list("devices")),1)
    def test_fitment_is_unverified(self):
        row=self.store.add("fitment",{"device_id":"pc1","module_id":"fan","part_id":"fan123"})
        self.assertFalse(row["verified"])
        self.assertEqual(len(self.store.compatible_parts("pc1","fan")),1)
    def test_fault_tree(self):
        row=self.store.add("fault_trees",{"category":"thermal","nodes":[
            {"id":"a","question":"Does the fan spin?","yes":"b","no":"b"},
            {"id":"b","action":"Observe fan RPM","action_type":"observe"}]})
        self.assertEqual(self.store.troubleshoot(row["id"])["node"]["id"],"a")
        self.assertEqual(self.store.troubleshoot(row["id"],{"a":True})["node"]["id"],"b")
    def test_rishi_review_not_approved(self):
        row=self.store.brahmagyan_handoff("case123","Vishvakarma","report:1")
        self.assertEqual(row["data"]["decision"],"pending_brahmagyan_exam")
    def test_no_destructive_tree_action(self):
        with self.assertRaises(PermissionError):
            self.store.add("fault_trees",{"category":"power","nodes":[
                {"id":"a","action":"Erase device","action_type":"execute"}]})
if __name__=="__main__":unittest.main()
