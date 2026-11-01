import tempfile
import unittest
from pathlib import Path
from krishna_core.sudarshan_lean_review import SudarshanLeanReview


class SudarshanLeanReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'one.py').write_text('def calculate():\n    return 1\n# shortcut: fast path, revisit after profiling\n')
        (self.root / 'two.py').write_text('from one import calculate\nprint(calculate())\n')
        self.review = SudarshanLeanReview(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_references_are_advisory(self):
        report = self.review.review(['one.py'])
        self.assertFalse(report['ready_to_merge'])
        self.assertTrue(any(x['kind'] == 'impact_candidates' for x in report['findings']))

    def test_debt(self):
        self.assertEqual(self.review.debt()[0]['line'], 3)

    def test_modes_and_deps(self):
        report = self.review.review(['one.py'], mode='ultra', proposed_dependencies=['package'])
        self.assertTrue(any(x['kind'] == 'scope_challenge' for x in report['findings']))
        self.assertTrue(any(x['kind'] == 'dependency_justification_required' for x in report['findings']))

    def test_path_traversal(self):
        with self.assertRaises(ValueError):
            self.review.review(['../outside.py'])

    def test_bad_mode(self):
        with self.assertRaises(ValueError):
            self.review.review(['one.py'], mode='unknown')
