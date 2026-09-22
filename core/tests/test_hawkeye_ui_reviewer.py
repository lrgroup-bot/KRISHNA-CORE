import tempfile
import unittest
from pathlib import Path

from krishna_core.hawkeye_ui_reviewer import HawkeyeUIReviewer


class FakeVision:
    def __init__(self,available=True,payload=None):
        self.available=available
        self.payload=payload or '{"passed":true,"summary":"clean","issues":[]}'
    def status(self):
        return {"provider":"fake","model":"fake-vision","local":True,"available":self.available}
    def analyze_bytes(self,data,content_type,prompt):
        return {"provider":"fake","model":"fake-vision","local":True,"analysis":self.payload}


class HawkeyeUIReviewerTests(unittest.TestCase):
    def test_clean_review_passes(self):
        with tempfile.TemporaryDirectory() as td:
            shot=Path(td)/"ui.png";shot.write_bytes(b"png")
            reviewer=HawkeyeUIReviewer(FakeVision(),max_images=4)
            result=reviewer.review([{"path":str(shot),"label":"mobile"}],{"geometry_findings":[]},required=True)
            self.assertTrue(result["passed"])
            self.assertEqual(result["review_count"],1)

    def test_high_confidence_error_blocks(self):
        payload='{"passed":false,"summary":"overlap","issues":[{"kind":"overlap","detail":"Primary button overlaps footer","severity":"error","confidence":0.95}]}'
        with tempfile.TemporaryDirectory() as td:
            shot=Path(td)/"ui.png";shot.write_bytes(b"png")
            result=HawkeyeUIReviewer(FakeVision(payload=payload)).review([{"path":str(shot)}],required=False)
            self.assertFalse(result["passed"])
            self.assertEqual(len(result["material_issues"]),1)

    def test_unavailable_blocks_only_when_required(self):
        reviewer=HawkeyeUIReviewer(FakeVision(available=False))
        self.assertTrue(reviewer.review([],required=False)["passed"])
        self.assertFalse(reviewer.review([],required=True)["passed"])


if __name__=="__main__":
    unittest.main()
