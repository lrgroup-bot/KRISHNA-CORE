import io
import json
import sqlite3
import unittest
from tools.sudarshan_brahmagyan import propose_lessons, review_lesson, approved_lessons

class FakeResponse:
    def __init__(self, payload):
        self.stream = io.BytesIO(json.dumps({'response': json.dumps(payload)}).encode())
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.stream.read(n)
    def geturl(self):return 'http://127.0.0.1:11434/api/generate'

class BrahmagyanTests(unittest.TestCase):
    def setUp(self):self.db=sqlite3.connect(':memory:')
    def tearDown(self):self.db.close()
    def test_requires_permission_and_locality(self):
        with self.assertRaises(PermissionError):
            propose_lessons(self.db,'p','f','r','e',['ev1'],model='local')
        with self.assertRaises(PermissionError):
            propose_lessons(self.db,'p','f','r','e',['ev1'],model='local',authorized=True,
                            endpoint='https://external.example/api/generate')
    def test_reviewed_learning_is_retrievable(self):
        fake=lambda request,timeout:FakeResponse({'lessons':[
            {'claim':'A button is missing','supporting_evidence':['ev1']}]})
        ids=propose_lessons(self.db,'p','f','Vyasa','The UI has no button',['ev1'],
                            model='qwen3:8b',authorized=True,transport=fake)
        self.assertEqual(len(ids),1)
        self.assertEqual(approved_lessons(self.db,'p','f'),[])
        review_lesson(self.db,'p','f',ids[0],'approved','owner')
        result=approved_lessons(self.db,'p','f')
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['claim'],'A button is missing')
        self.assertEqual(result[0]['sources'],['ev1'])
    def test_model_cannot_invent_evidence(self):
        fake=lambda request,timeout:FakeResponse({'lessons':[
            {'claim':'False','supporting_evidence':['invented']}]})
        with self.assertRaises(ValueError):
            propose_lessons(self.db,'p','f','Vyasa','original',['ev1'],
                            model='local',authorized=True,transport=fake)
        self.assertEqual(approved_lessons(self.db,'p','f'),[])

if __name__=='__main__':unittest.main()
