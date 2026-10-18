import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.sudarshan_cli import main

class CliTests(unittest.TestCase):
 def test_explicit_approval_required(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/"config.json"
   path.write_text("{}")
   with self.assertRaises(SystemExit) as caught:
    main(["--config",str(path)])
   self.assertEqual(caught.exception.code,2)
 def test_missing_config_fields_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/"config.json"
   path.write_text(json.dumps({"project_id":"p"}))
   with self.assertRaises(SystemExit) as caught:
    main(["--config",str(path),"--approve-local-run"])
   self.assertEqual(caught.exception.code,2)
 def test_empty_adapter_config_rejected(self):
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/"config.json"
   path.write_text(json.dumps({"project_id":"p","feature_id":"f","db_path":"data.sqlite","adapters":{}}))
   with self.assertRaises(ValueError):
    main(["--config",str(path),"--approve-local-run"])

if __name__=="__main__":unittest.main()
