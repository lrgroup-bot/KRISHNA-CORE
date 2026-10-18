import tempfile
import unittest
from pathlib import Path
from tools.sudarshan_execution_contract import AdapterResult
from tools.sudarshan_knowledge_store import connect,record,history

class KnowledgeTests(unittest.TestCase):
 def test_persistent_idempotent_history(self):
  with tempfile.TemporaryDirectory() as root:
   path=str(Path(root)/"evidence.sqlite")
   db=connect(path)
   result=AdapterResult("BRAHMAGYAN","passed","source:1","reviewed evidence")
   first=record(db,"project","feature",result)
   self.assertEqual(first,record(db,"project","feature",result))
   db.close()
   db=connect(path)
   items=history(db,"project","feature")
   self.assertEqual(len(items),1)
   self.assertEqual(items[0]["digest"],first)
   self.assertEqual(history(db,"other","feature"),[])
   db.close()
 def test_invalid_evidence_rejected(self):
  db=connect(":memory:")
  with self.assertRaises(ValueError):
   record(db,"p","f",AdapterResult("REA","passed","",""))
  db.close()

if __name__=="__main__":unittest.main()
