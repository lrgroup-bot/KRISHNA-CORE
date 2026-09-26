import tempfile
import unittest
from pathlib import Path

from krishna_core.vanijya_sales import PERMANENT_TEAM, VanijyaSalesHead


class StubCRM:
    def __init__(self, products=None):
        self.products=list(products or [])
        self.moves=[]

    def records(self):
        return {"products":list(self.products)}

    def move_deal(self,deal_id,stage):
        self.moves.append((deal_id,stage))
        return {"id":deal_id,"stage":stage}


class StubMessages:
    def __init__(self):
        self.rows=[]

    def add(self,**row):
        row=dict(row)
        row.setdefault("id","MSG-"+str(len(self.rows)+1))
        self.rows.append(row)
        return dict(row)

    def list(self,**kwargs):
        rows=list(reversed(self.rows))
        if kwargs.get("direction"):
            rows=[x for x in rows if x.get("direction")==kwargs["direction"]]
        if kwargs.get("state"):
            rows=[x for x in rows if x.get("state")==kwargs["state"]]
        if kwargs.get("provider"):
            rows=[x for x in rows if x.get("provider")==kwargs["provider"]]
        return rows[:kwargs.get("limit",200)]


class StubWorkerRuntime:
    def __init__(self):
        self.requests=[]

    def execute(self,project,request,task,privacy):
        self.requests.append({
            "project":project,"request":dict(request),"task":task,"privacy":privacy,
        })
        return {
            "batch_id":"batch-1",
            "destroyed":True,
            "live_after_return":False,
            "workers":[{"worker_id_hash":"abc","specialty":request["role"],"result":"{}"}],
        }


class VanijyaSalesTests(unittest.TestCase):
    def runtime(self,root,products=None,messages=None,crm=None):
        return VanijyaSalesHead(
            Path(root)/"vanijya-sales.json",
            crm=crm or StubCRM(products),
            message_store=messages,
        )

    def test_vanijya_is_independent_sales_marketing_head(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            status=v.status()
            self.assertTrue(status["independent"])
            self.assertEqual(status["title"],"Independent Sales & Marketing Head")
            self.assertTrue(status["asks_manibhadra_for_products"])
            self.assertEqual(status["communications_owner"],"NARAD")
            self.assertEqual(len(PERMANENT_TEAM),8)
            self.assertEqual({x.id for x in PERMANENT_TEAM},{
                "lead-researcher","sdr-caller","lead-qualifier","account-executive",
                "solution-consultant","proposal-pricing","deal-closer","relationship-manager",
            })

    def test_persistent_state_roundtrip_and_health(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            v.hr_request("export follow-up specialist")
            again=VanijyaSalesHead(Path(td)/"vanijya-sales.json")
            self.assertEqual(again.status()["counts"]["hr_requests"],1)
            self.assertTrue(again.health()["ok"])

    def test_hr_request_create_and_retire_preserves_guardrails_and_learning(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            req=v.hr_request("multilingual export follow-up specialist",reason="Hindi and Odia follow-up")
            self.assertIn("zero_spend",req["must_inherit"])
            self.assertIn("honor_opt_out",req["must_inherit"])
            bot=v.hr_create_bot(req["request_id"],name="Export Follow-up Shishya",skills=["Hindi","Odia"])
            self.assertEqual(bot["reports_to"],"rishi-vanijya")
            self.assertEqual(bot["status"],"READY")
            self.assertIn("receive_only",bot["guardrails"])
            retired=v.hr_retire_bot(bot["id"],outcome="campaign complete",lessons=["pricing question converts well"])
            self.assertEqual(retired["status"],"RETIRED")
            self.assertEqual(retired["lessons"],["pricing question converts well"])

    def test_real_hr_plan_is_preapproved_by_krishna_and_workers_retire(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            workers=StubWorkerRuntime()
            v.bind_worker_runtime(workers)
            plan=v.hr_plan("Call qualified leads in Hindi",role_ids=["sdr-caller"],requested_count=2)
            req=plan["requests"][0]
            self.assertEqual(req["status"],"approved")
            self.assertEqual(req["approved_by"],"KRISHNA")
            self.assertEqual(req["manager"],"rishi:vanijya")
            self.assertEqual(req["retention_policy"],"findings_and_provenance_only")
            result=v.execute_hr_plan("KRISHNA","Call qualified leads in Hindi",role_ids=["sdr-caller"],requested_count=2,privacy="local_only")
            self.assertTrue(result["all_workers_retire_after_handover"])
            self.assertEqual(workers.requests[0]["request"]["approved_by"],"KRISHNA")
            self.assertEqual(workers.requests[0]["privacy"],"local_only")

    def test_syncs_manibhadra_products_without_fabricating_products(self):
        with tempfile.TemporaryDirectory() as td:
            products=[{"id":"p1","name":"Website Service","sale_price":15000,"source":"our product","status":"ready"}]
            v=self.runtime(td,products)
            out=v.sync_manibhadra_products()
            self.assertEqual(out["synced"],1)
            self.assertEqual(out["products"][0]["product_id"],"p1")
            self.assertEqual(out["products"][0]["sale_price"],15000)
            self.assertEqual(v.sync_manibhadra_products()["synced"],0)

    def test_sales_cycle_asks_manibhadra_when_no_product_exists(self):
        with tempfile.TemporaryDirectory() as td:
            out=self.runtime(td,[]).sales_cycle()
            self.assertEqual(out["status"],"NEEDS_PRODUCT")
            self.assertEqual(out["next"]["to"],"manibhadra")

    def test_sales_cycle_uses_approved_manibhadra_product_and_all_agents(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td,[{"id":"p1","name":"CRM Setup","sale_price":20000,"source":"our product","status":"ready"}])
            out=v.sales_cycle()
            self.assertEqual(out["status"],"READY")
            self.assertEqual(out["product"]["name"],"CRM Setup")
            self.assertEqual([x["agent"] for x in out["workflow"]],[x.id for x in PERMANENT_TEAM])
            self.assertTrue(out["zero_spend"])
            self.assertEqual(out["communications_via"],"NARAD")

    def test_autopilot_always_requests_manibhadra_and_assigns_sales_agents(self):
        with tempfile.TemporaryDirectory() as td:
            products=[{"id":"p1","name":"Website Service","sale_price":15000,"source":"our product","status":"ready"}]
            crm=StubCRM(products)
            crm.records=lambda:{
                "products":products,
                "leads":[{"id":"l1","stage":"new","score":80,"next_action":"Call buyer"}],
                "deals":[{"id":"d1","stage":"negotiation","next_action":"Confirm terms"}],
                "tasks":[{"id":"t1","status":"open","priority":"high","title":"Follow up"}],
            }
            v=self.runtime(td,crm=crm)
            out=v.autopilot_plan()
            self.assertEqual(out["manibhadra_request"]["to"],"manibhadra")
            self.assertFalse(out["external_send_performed"])
            self.assertFalse(out["spend_performed"])
            agents={x["agent"] for x in out["agent_queue"]}
            self.assertTrue({"lead-qualifier","deal-closer","relationship-manager"}.issubset(agents))

    def test_campaign_is_zero_spend_and_paid_acquisition_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            c=self.runtime(td).create_campaign(
                {"id":"p1","name":"Website Service","sale_price":10000},
                channels=["gmail","whatsapp"],audience="retailers without websites",geography="Odisha",
            )
            self.assertEqual(c["status"],"active")
            self.assertEqual(c["acquisition_cost_limit"],0)
            self.assertFalse(c["paid_ads"])
            self.assertFalse(c["paid_leads"])

    def test_outreach_fails_closed_when_connector_missing(self):
        verdict=VanijyaSalesHead.outreach_decision(
            {"public_business_contact":True},channel="gmail",connector_state="WAITING_FOR_CONNECTION",
        )
        self.assertFalse(verdict["allowed"])
        self.assertIn("connector_not_connected",verdict["reasons"])

    def test_outreach_blocks_opt_out_and_private_unconsented_contact(self):
        opted=VanijyaSalesHead.outreach_decision(
            {"consented":True,"last_message":"Please unsubscribe me"},
            channel="email",connector_state="CONNECTED",
        )
        self.assertIn("opted_out",opted["reasons"])
        private=VanijyaSalesHead.outreach_decision(
            {"email":"private@example.com"},channel="gmail",connector_state="CONNECTED",
        )
        self.assertFalse(private["allowed"])
        self.assertIn("no_public_or_consented_contact_basis",private["reasons"])

    def test_marketing_plan_requires_manibhadra_and_never_enables_paid_media(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            waiting=v.marketing_plan({"name":"CRM Service"},manibhadra_checked=False)
            self.assertEqual(waiting["status"],"waiting_for_manibhadra")
            ready=v.marketing_plan({"name":"CRM Service"},manibhadra_checked=True)
            self.assertFalse(ready["paid_media"])
            self.assertFalse(ready["paid_leads"])
            self.assertTrue(ready["zero_spend"])

    def test_whatsapp_public_number_alone_is_not_enough_for_automatic_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            plan=self.runtime(td).outreach_plan(
                "whatsapp",
                {
                    "phone":"+911234567890",
                    "contact_basis":"public_business_contact_for_relevant_b2b",
                    "connector_state":"CONNECTED",
                },
                purpose="Product introduction",
                body="A truthful relevant business introduction.",
            )
            self.assertFalse(plan["can_enter_automatic_send_workflow"])
            self.assertIn("NARADA Legal",plan["legal_gate"])

    def test_lead_qualification_routes_only_real_fit_to_account_executive(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            q=v.qualify_lead({"id":"lead1"},{"need":90,"fit":90,"engagement":80,"timing":70,"authority":60})
            self.assertTrue(q["qualified"])
            self.assertEqual(q["next_agent"],"account-executive")
            weak=v.qualify_lead({"id":"lead2"},{"need":20,"fit":20,"engagement":10})
            self.assertFalse(weak["qualified"])
            self.assertEqual(weak["stage"],"nurture")

    def test_customer_reply_and_opt_out_routing(self):
        with tempfile.TemporaryDirectory() as td:
            messages=StubMessages()
            v=self.runtime(td,messages=messages)
            row=v.ingest_reply(
                lead_id="lead1",provider="gmail",sender="buyer@example.com",
                text="Please send the price and quotation",thread_ref="thread-1",
            )
            self.assertEqual(row["intent"],"pricing")
            self.assertEqual(row["next"]["agent"],"proposal-pricing")
            self.assertEqual(messages.rows[-1]["direction"],"inbox")
            opt=v.ingest_reply(
                lead_id="lead2",provider="whatsapp",sender="+910000000000",
                text="Stop. Do not contact me again.",
            )
            self.assertEqual(opt["intent"],"opt_out")
            self.assertEqual(opt["status"],"opted_out")

    def test_outbound_plan_records_narad_outbox_and_provider_payload(self):
        with tempfile.TemporaryDirectory() as td:
            messages=StubMessages()
            v=self.runtime(td,messages=messages)
            lead={"id":"l1","email":"buyer@example.com","consented":True}
            out=v.plan_outbound(
                lead=lead,channel="gmail",connector_state="CONNECTED",
                subject="CRM proposal",text="Here is the requested information.",thread_ref="thread-1",
            )
            self.assertEqual(out["status"],"queued")
            self.assertEqual(messages.rows[-1]["direction"],"outbox")
            spec=v.provider_payload(out,lead)
            self.assertEqual(spec["provider"],"gmail")
            self.assertEqual(spec["operation"],"send_email")
            self.assertEqual(spec["payload"]["text"],"Here is the requested information.")
            self.assertEqual(spec["payload"]["thread_id"],"thread-1")

    def test_narad_inbox_processor_matches_sales_thread_and_routes_reply(self):
        with tempfile.TemporaryDirectory() as td:
            messages=StubMessages()
            v=self.runtime(td,messages=messages)
            lead={"id":"l1","email":"buyer@example.com","consented":True}
            v.plan_outbound(
                lead=lead,channel="gmail",connector_state="CONNECTED",
                subject="Proposal",text="Here is our proposal.",thread_ref="thread-1",
            )
            messages.rows.append({
                "id":"MSG-IN-1","direction":"inbox","provider":"gmail","thread_ref":"thread-1",
                "sender":"buyer@example.com","text":"Please send the price and quotation.",
                "metadata":{},"state":"received",
            })
            out=v.process_narad_inbox()
            self.assertEqual(out["processed"],1)
            self.assertEqual(out["results"][0]["lead_id"],"l1")
            self.assertEqual(out["results"][0]["intent"],"pricing")
            self.assertEqual(v.process_narad_inbox()["processed"],0)

    def test_quote_uses_catalogue_price_and_rejects_unapproved_discount(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            product={"id":"p1","name":"Service","sale_price":"1000","approved_discount_percent":10}
            q=v.quote(lead_id="l1",product=product,quantity=2,approved_discount_percent=10)
            self.assertEqual(q["subtotal"],2000.0)
            self.assertEqual(q["amount_due"],1800.0)
            self.assertEqual(q["truth_source"],"MANIBHADRA product record")
            with self.assertRaises(PermissionError):
                v.quote(lead_id="l1",product=product,quantity=1,approved_discount_percent=20)

    def test_exact_amount_upi_request_qr_and_untrusted_payment_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            req=v.upi_payment_request(
                payee_vpa="merchant@example",payee_name="Example Merchant",
                amount="1250",invoice_id="INV-1",deal_id="deal-1",lead_id="lead-1",
            )
            self.assertEqual(req["amount"],1250.0)
            self.assertTrue(req["receive_only"])
            self.assertIn("am=1250.00",req["upi_uri"])
            self.assertEqual(req["status"],"PENDING")
            qr=v.payment_qr_svg(req)
            self.assertFalse(qr["payment_proof"])
            if qr["available"]:
                self.assertEqual(qr["mime_type"],"image/svg+xml")
                self.assertTrue(qr["data_uri"].startswith("data:image/svg+xml;base64,"))
            else:
                self.assertIn("INSTALL_KRISHNA_QR.ps1",qr["install"])
            result=v.verify_payment(req,{
                "provider":"customer_screenshot","source":"screenshot","signature_verified":False,"status":"SUCCESS",
                "invoice_id":"INV-1","amount":"1250","transaction_id":"claimed",
            })
            self.assertFalse(result["paid"])
            self.assertIn("unverified_evidence",result["reasons"])
            self.assertIn("untrusted_payment_source",result["reasons"])

    def test_verified_provider_exact_payment_moves_linked_deal_to_won(self):
        with tempfile.TemporaryDirectory() as td:
            crm=StubCRM()
            v=self.runtime(td,crm=crm)
            req=v.upi_payment_request(
                payee_vpa="merchant@example",payee_name="Example Merchant",
                amount="1250",invoice_id="INV-1",deal_id="deal-1",
            )
            result=v.verify_payment(req,{
                "provider":"gateway","source":"payment_gateway_webhook","signature_verified":True,"status":"CAPTURED",
                "invoice_id":"INV-1","amount":"1250","transaction_id":"pay_123",
            })
            self.assertTrue(result["paid"])
            self.assertEqual(result["status"],"PAID")
            self.assertEqual(crm.moves,[("deal-1","won")])
            self.assertEqual(v.status()["counts"]["paid_payments"],1)

    def test_pipeline_cannot_close_before_verified_payment_and_blueprint_preserves_boundaries(self):
        with tempfile.TemporaryDirectory() as td:
            v=self.runtime(td)
            self.assertEqual(v.pipeline_next("payment_pending",payment_verified=False)["stage"],"payment_pending")
            self.assertEqual(v.pipeline_next("payment_pending",payment_verified=True)["stage"],"won")
            blueprint=v.automation_blueprint()
            self.assertIn("NARAD"," ".join(blueprint["product_loop"]))
            self.assertTrue(any("outgoing money" in x for x in blueprint["never"]))


if __name__=="__main__":
    unittest.main()
