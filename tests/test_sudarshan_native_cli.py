import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.sudarshan_execution_contract import AdapterResult
from tools.sudarshan_native_cli import main, dispatch

class NativeCliTests(unittest.TestCase):
    def test_requires_approval(self):
        with tempfile.TemporaryDirectory() as root:
            spec=Path(root)/'spec.json';spec.write_text('{}')
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ex:
                    main(['--engine','REA','--spec',str(spec)])
            self.assertEqual(ex.exception.code,2)
    def test_nonpass_output_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            spec=Path(root)/'spec.json';spec.write_text('{}')
            with patch('tools.sudarshan_native_cli.dispatch',return_value=AdapterResult('REA','not_tested','','needs service')):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(['--engine','REA','--spec',str(spec),'--approve-local-run']),0)
            self.assertEqual(json.loads(output.getvalue())['status'],'not_tested')
    def test_dispatch_never_bypasses_authorization(self):
        with self.assertRaises(PermissionError):dispatch('REA',{})
    def test_unrecognized_engine(self):
        with self.assertRaises(ValueError):dispatch('OTHER',{},authorized=True)

if __name__=='__main__':unittest.main()
