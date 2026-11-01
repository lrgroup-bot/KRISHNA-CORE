import tempfile
import unittest
from pathlib import Path
from krishna_core.garuda_repair_studio import create_repair_case, export_case

class GarudaRepairStudioTests(unittest.TestCase):
    def test_repeatable_case_id(self):
        a=create_repair_case("pc-1","storage","Disk disconnects intermittently",["report:123"])
        b=create_repair_case("pc-1","storage","Disk disconnects intermittently",["report:123"])
        self.assertEqual(a.case_id,b.case_id)
        self.assertEqual(a.status,"draft")
    def test_reject_unknown_categories(self):
        with self.assertRaises(ValueError):
            create_repair_case("pc-1","firmware_flash","Please flash BIOS")
    def test_power_case_requires_technician(self):
        self.assertTrue(create_repair_case("pc-1","power","Power cuts randomly").requires_technician)
    def test_never_overwrite(self):
        case=create_repair_case("pc-1","software","App fails to start")
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"case.json"
            export_case(case,path)
            with self.assertRaises(FileExistsError):
                export_case(case,path)
if __name__=="__main__":
    unittest.main()
