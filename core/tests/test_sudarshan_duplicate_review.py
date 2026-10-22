import tempfile
import unittest
from pathlib import Path
from krishna_core.sudarshan_duplicate_review import duplicate_candidates

class DuplicateReviewTests(unittest.TestCase):
    def test_detects_structural_clone(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            (p/"a.py").write_text("def foo(x):\n if x:\n  return x+1\n else:\n  return x-1\n")
            (p/"b.py").write_text("def bar(y):\n if y:\n  return y+2\n else:\n  return y-3\n")
            result=duplicate_candidates(p)
            self.assertEqual(len(result["candidates"]),1)
            self.assertEqual(result["candidates"][0]["status"],"review_only")
    def test_ignores_small_functions(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)
            (p/"a.py").write_text("def a():\n return 1\n")
            (p/"b.py").write_text("def b():\n return 2\n")
            self.assertEqual(duplicate_candidates(p)["candidates"],[])
if __name__=="__main__":unittest.main()
