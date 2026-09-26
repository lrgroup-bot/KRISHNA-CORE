import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from krishna_core.manibhadra_advisor import ManibhadraCloudAdvisor
from krishna_core.manibhadra_crm import ManibhadraCRM


class FakeOpenRouter:
    def __init__(self, configured=True, fail=False):
        self._configured=configured
        self.fail=fail
    def configured(self): return self._configured
    def complete(self, role, prompt, **kwargs):
        if self.fail: raise RuntimeError("openrouter failed")
        return {"model":"free-reasoner","text":"{\"summary\":\"focus on hot leads\"}","zero_cost_verified":True}


class FakeDirect:
    def __init__(self, configured=True):
        self._configured=configured
    def configured(self): return self._configured
    def complete(self, prompt, **kwargs):
        return {"provider":"direct-free:cloudflare-workers-ai","model":"free","text":"fallback","zero_cost_verified":True}


class ManibhadraCRMTests(unittest.TestCase):
    def test_empty_dashboard_contains_no_fake_revenue(self):
        with tempfile.TemporaryDirectory() as td:
            crm=ManibhadraCRM(Path(td)/"crm.json")
            d=crm.dashboard()
            self.assertEqual(d["kpis"]["pipeline_value"],0)
            self.assertEqual(d["kpis"]["won_commission"],0)
            self.assertEqual(d["attention"],[])
            self.assertTrue(d["zero_spend"])

    def test_lead_deal_pipeline_and_attention(self):
        with tempfile.TemporaryDirectory() as td:
            crm=ManibhadraCRM(Path(td)/"crm.json")
            lead=crm.upsert_lead({"name":"Buyer A","intent":"smartwatch","source":"social","score":88})
            deal=crm.upsert_deal({
                "title":"Watch referral","lead_id":lead["id"],"value":10000,
                "expected_commission":800,"stage":"qualified",
            })
            data=json.loads((Path(td)/"crm.json").read_text(encoding="utf-8"))
            row=next(x for x in data["deals"] if x["id"]==deal["id"])
            row["last_touched_at"]=(datetime.now(timezone.utc)-timedelta(days=10)).isoformat()
            (Path(td)/"crm.json").write_text(json.dumps(data),encoding="utf-8")
            d=crm.dashboard()
            self.assertEqual(d["kpis"]["active_deals"],1)
            self.assertEqual(d["kpis"]["pipeline_value"],10000)
            self.assertGreater(d["kpis"]["expected_commission"],0)
            self.assertTrue(any(x["kind"]=="deal" for x in d["attention"]))
            self.assertTrue(any(x["kind"]=="lead" for x in d["attention"]))

    def test_move_deal_and_won_commission(self):
        with tempfile.TemporaryDirectory() as td:
            crm=ManibhadraCRM(Path(td)/"crm.json")
            deal=crm.upsert_deal({"title":"Affiliate order","value":5000,"expected_commission":500})
            moved=crm.move_deal(deal["id"],"won")
            self.assertEqual(moved["stage"],"won")
            d=crm.dashboard()
            self.assertEqual(d["kpis"]["won_commission"],500)
            self.assertEqual(d["kpis"]["active_deals"],0)

    def test_tasks_and_entities_are_real_records(self):
        with tempfile.TemporaryDirectory() as td:
            crm=ManibhadraCRM(Path(td)/"crm.json")
            supplier=crm.upsert_entity("supplier",{"company":"Odisha Supplier","location":"Bhubaneswar"})
            product=crm.upsert_entity("product",{"name":"Steel bottle","supplier_id":supplier["id"],"sale_price":899})
            task=crm.add_task({"title":"Call supplier","priority":"high"})
            self.assertEqual(product["name"],"Steel bottle")
            self.assertEqual(crm.complete_task(task["id"])["status"],"done")
            rows=crm.records()
            self.assertEqual(len(rows["suppliers"]),1)
            self.assertEqual(len(rows["products"]),1)

    def test_backup_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"crm.json"
            crm=ManibhadraCRM(path)
            crm.upsert_lead({"name":"Buyer"})
            crm.upsert_lead({"name":"Buyer 2"})
            self.assertTrue(crm.backup.exists())
            path.write_text("{bad",encoding="utf-8")
            recovered=crm.records()
            self.assertGreaterEqual(len(recovered["leads"]),1)
            self.assertTrue(crm.health()["ok"])


class ManibhadraAdvisorTests(unittest.TestCase):
    def test_verified_free_cloud_is_primary(self):
        advisor=ManibhadraCloudAdvisor(FakeOpenRouter(),FakeDirect())
        out=advisor.advise("next action",{"kpis":{},"attention":[],"pipeline":[],"connections":[],"counts":{}})
        self.assertEqual(out["provider"],"openrouter-free")
        self.assertTrue(out["zero_cost_verified"])
        self.assertFalse(out["paid_fallback"])

    def test_verified_free_direct_provider_is_fallback(self):
        advisor=ManibhadraCloudAdvisor(FakeOpenRouter(fail=True),FakeDirect())
        out=advisor.advise("next action",{"kpis":{},"attention":[],"pipeline":[],"connections":[],"counts":{}})
        self.assertIn("cloudflare",out["provider"])
        self.assertFalse(out["paid_fallback"])

    def test_no_paid_or_local_fallback_is_claimed(self):
        advisor=ManibhadraCloudAdvisor(FakeOpenRouter(configured=False),FakeDirect(configured=False))
        with self.assertRaises(RuntimeError):
            advisor.advise("next action",{"kpis":{},"attention":[],"pipeline":[],"connections":[],"counts":{}})


if __name__=="__main__":
    unittest.main()
