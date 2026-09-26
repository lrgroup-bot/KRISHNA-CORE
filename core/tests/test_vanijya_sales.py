from __future__ import annotations

import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from krishna_core.rishi_council import RishiCouncil
from krishna_core.vanijya_sales import SALES_TEAM, VanijyaSalesHead
from krishna_core.zero_spend_policy import ZeroSpendPolicy


class Stub:
    pass


class CRMStub:
    def __init__(self):
        self.leads=[]
        self.deals=[]

    def dashboard(self):
        return {"ok":True,"total_leads":len(self.leads),"active_deals":len(self.deals)}

    def upsert_lead(self,row):
        self.leads.append(dict(row))
        return self.leads[-1]

    def upsert_deal(self,row):
        self.deals.append(dict(row))
        return self.deals[-1]


class WorkerStub:
    def __init__(self):
        self.requests=[]

    def execute(self,project,request,task,privacy):
        self.requests.append((project,request,task,privacy))
        return {"batch_id":"b1","destroyed":True,"workers":[]}


class VanijyaSalesHeadTests(unittest.TestCase):
    def setUp(self):
        self.crm=CRMStub()
        self.vanijya=VanijyaSalesHead(self.crm,Stub(),ZeroSpendPolicy(),Stub())

    def test_rishi_vanijya_is_permanent_council_profile(self):
        profile=RishiCouncil().get("vanijya")
        self.assertEqual(profile["display_name"],"Rishi Vanijya")
        self.assertIn("Sales & Marketing Head",profile["role"])

    def test_exact_named_sales_team_is_present(self):
        self.assertEqual([x.name for x in SALES_TEAM],[
            "Lead Researcher",
            "SDR / Calling Shishya",
            "Lead Qualifier",
            "Account Executive",
            "Solution Consultant",
            "Proposal & Pricing Specialist",
            "Negotiator / Deal Closer",
            "Customer Relationship Manager",
        ])

    def test_hr_plan_is_bounded_and_parented_by_vanijya(self):
        plan=self.vanijya.hr_plan(
            "Qualify inbound enquiries",
            role_ids=["lead-qualifier","account-executive"],
            requested_count=20,
        )
        self.assertEqual(len(plan["requests"]),2)
        self.assertTrue(all(x["parent_rishi"]=="vanijya" for x in plan["requests"]))
        self.assertTrue(all(x["manager"]=="rishi:vanijya" for x in plan["requests"]))
        self.assertTrue(all(x["requested_count"]==8 for x in plan["requests"]))
        self.assertTrue(all(x["retire_after_handover"] for x in plan["requests"]))

    def test_hr_execute_reuses_ephemeral_worker_runtime(self):
        workers=WorkerStub()
        self.vanijya.bind_worker_runtime(workers)
        out=self.vanijya.execute_hr_plan(
            "KRISHNA","Research target accounts",role_ids=["lead-researcher"],requested_count=2
        )
        self.assertTrue(out["all_workers_retire_after_handover"])
        self.assertEqual(len(workers.requests),1)
        self.assertEqual(workers.requests[0][1]["role"],"lead-researcher")

    def test_new_campaign_asks_manibhadra_first(self):
        req=self.vanijya.product_request("")
        self.assertEqual(req["to"],"MANIBHADRA")
        self.assertTrue(req["required_before_new_campaign"])
        self.assertEqual(req["next_action"],"manibhadra.research")

    def test_marketing_plan_requires_manibhadra_check_and_is_zero_spend(self):
        waiting=self.vanijya.marketing_plan({"name":"Example Service"})
        self.assertEqual(waiting["status"],"waiting_for_manibhadra")
        self.assertEqual(waiting["required_action"],"manibhadra.research")

        plan=self.vanijya.marketing_plan({"name":"Example Service"},manibhadra_checked=True)
        self.assertTrue(plan["manibhadra_checked"])
        self.assertFalse(plan["paid_media"])
        self.assertIn("paid advertising under zero-spend mode",plan["prohibitions"])

    def test_suppressed_lead_never_qualifies(self):
        result=self.vanijya.qualify_lead({
            "requirement":"Need product",
            "email":"buyer@example.com",
            "score":90,
            "inbound":True,
            "opted_out":True,
        })
        self.assertFalse(result["qualified"])
        self.assertTrue(result["suppressed"])

    def test_whatsapp_promotional_plan_requires_opt_in_or_inbound(self):
        blocked=self.vanijya.outreach_plan(
            "whatsapp",
            {"phone":"919999999999","contact_basis":"public_business_contact_for_relevant_b2b"},
            purpose="Product introduction",
            body="Hello",
        )
        self.assertFalse(blocked["can_enter_automatic_send_workflow"])

        allowed=self.vanijya.outreach_plan(
            "whatsapp",
            {"phone":"919999999999","opt_in":True},
            purpose="Requested product details",
            body="Here are the details you requested.",
        )
        self.assertTrue(allowed["can_enter_automatic_send_workflow"])
        self.assertEqual(allowed["provider_action"]["action"],"narad.provider_send")
        self.assertEqual(allowed["provider_action"]["provider"],"whatsapp")

    def test_email_relevant_b2b_contact_is_still_legal_gated(self):
        row=self.vanijya.outreach_plan(
            "gmail",
            {"email":"buyer@example.com","contact_basis":"public_business_contact_for_relevant_b2b"},
            purpose="Relevant B2B introduction",
            subject="Product fit",
            body="Short relevant business introduction.",
        )
        self.assertTrue(row["can_enter_automatic_send_workflow"])
        self.assertIn("NARADA Legal",row["legal_gate"])
        self.assertTrue(row["opt_out_must_be_honored"])

    def test_opt_out_reply_stops_sales_followup(self):
        row=self.vanijya.inbound_reply_plan({"text":"Please unsubscribe and do not contact me."})
        self.assertEqual(row["intent"],"opt_out")
        self.assertTrue(row["must_not_sell"])

    def test_purchase_reply_routes_to_deal_closer(self):
        row=self.vanijya.inbound_reply_plan({"text":"We want to proceed. Send payment link."})
        self.assertEqual(row["intent"],"purchase_intent")
        self.assertEqual(row["next_role"],"negotiator-deal-closer")

    def test_shared_crm_is_used(self):
        self.vanijya.save_lead({"name":"Buyer","intent":"Example"})
        self.vanijya.save_deal({"title":"Deal","value":100})
        dash=self.vanijya.crm_snapshot()
        self.assertEqual(dash["total_leads"],1)
        self.assertEqual(dash["active_deals"],1)

    def test_rich_vanijya_stages_map_to_canonical_crm_stages(self):
        lead=self.vanijya.save_lead({"name":"Buyer","intent":"Need product","stage":"discovery"})
        deal=self.vanijya.save_deal({"title":"Deal","value":100,"stage":"closed_won"})
        self.assertEqual(lead["stage"],"qualified")
        self.assertEqual(deal["stage"],"won")

    def test_payment_request_is_receive_only_and_exact_amount(self):
        row=self.vanijya.payment_request(
            payee_vpa="merchant@upi",
            payee_name="Example Merchant",
            amount="499",
            order_ref="ORDER-42",
            note="Order 42",
        )
        self.assertEqual(row["status"],"pending_unverified")
        self.assertTrue(row["verification_required"])
        self.assertTrue(row["money_policy"]["allowed"])
        self.assertEqual(row["money_policy"]["direction"],"incoming")
        parsed=urlparse(row["upi_uri"])
        self.assertEqual(parsed.scheme,"upi")
        qs=parse_qs(parsed.query)
        self.assertEqual(qs["am"],["499.00"])
        self.assertEqual(qs["cu"],["INR"])
        self.assertEqual(qs["tr"],["ORDER-42"])

    def test_qr_renderer_is_local_and_fail_closed(self):
        request=self.vanijya.payment_request(
            payee_vpa="merchant@upi",payee_name="Example Merchant",
            amount="99",order_ref="ORDER-QR",
        )
        result=self.vanijya.payment_qr_svg(request)
        self.assertIn("available",result)
        if result["available"]:
            self.assertEqual(result["mime_type"],"image/svg+xml")
            self.assertTrue(result["data_uri"].startswith("data:image/svg+xml;base64,"))
            self.assertFalse(result["payment_proof"])
        else:
            self.assertIn("INSTALL_KRISHNA_QR.ps1",result["install"])

    def test_customer_claim_screenshot_or_redirect_never_verifies_payment(self):
        for source in ("customer_claim","customer_message","screenshot","browser_redirect"):
            row=self.vanijya.verify_payment({
                "source":source,
                "status":"success",
                "amount":"499.00",
                "order_ref":"ORDER-42",
                "utr":"123456789",
            },expected_amount="499",expected_order_ref="ORDER-42")
            self.assertFalse(row["verified"])

    def test_trusted_payment_requires_amount_reference_and_transaction_id(self):
        good=self.vanijya.verify_payment({
            "source":"payment_gateway_webhook",
            "status":"captured",
            "amount":"499.00",
            "order_ref":"ORDER-42",
            "utr":"123456789012",
        },expected_amount="499",expected_order_ref="ORDER-42")
        self.assertTrue(good["verified"])
        self.assertEqual(good["next_stage"],"closed_won")

        bad=self.vanijya.verify_payment({
            "source":"payment_gateway_webhook",
            "status":"captured",
            "amount":"498.00",
            "order_ref":"ORDER-42",
            "utr":"123456789012",
        },expected_amount="499",expected_order_ref="ORDER-42")
        self.assertFalse(bad["verified"])
        self.assertEqual(bad["status"],"amount_mismatch")

    def test_payment_pending_does_not_close_without_verification(self):
        self.assertEqual(
            self.vanijya.pipeline_next("payment_pending",payment_verified=False)["stage"],
            "payment_pending",
        )
        self.assertEqual(
            self.vanijya.pipeline_next("payment_pending",payment_verified=True)["stage"],
            "closed_won",
        )

    def test_orchestrator_exposes_vanijya_actions_and_independent_agent(self):
        source=(Path(__file__).resolve().parents[1]/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        for token in (
            '"vanijya.status"',
            '"vanijya.hr.execute"',
            '"vanijya.product.scout"',
            '"vanijya.marketing.plan"',
            '"vanijya.outreach.plan"',
            '"vanijya.inbound.reply"',
            '"vanijya.payment.request"',
            '"vanijya.payment.qr"',
            '"vanijya.payment.verify"',
            '"vanijya","independent sales and marketing head',
        ):
            self.assertIn(token,source)


if __name__=="__main__":
    unittest.main()
