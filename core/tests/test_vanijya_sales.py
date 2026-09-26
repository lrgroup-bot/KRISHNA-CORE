import tempfile
from pathlib import Path

import pytest

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
        self.rows.append(dict(row))
        return dict(row)


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


def make_runtime(tmp_path,products=None,messages=None):
    return VanijyaSalesHead(
        tmp_path/"vanijya-sales.json",
        crm=StubCRM(products),
        message_store=messages,
    )


def test_vanijya_is_independent_sales_marketing_head(tmp_path):
    v=make_runtime(tmp_path)
    status=v.status()
    assert status["independent"] is True
    assert status["title"]=="Independent Sales & Marketing Head"
    assert status["asks_manibhadra_for_products"] is True
    assert status["communications_owner"]=="NARAD"
    assert len(PERMANENT_TEAM)==8
    assert {x.id for x in PERMANENT_TEAM}=={
        "lead-researcher","sdr-caller","lead-qualifier","account-executive",
        "solution-consultant","proposal-pricing","deal-closer","relationship-manager",
    }


def test_persistent_state_roundtrip_and_health(tmp_path):
    v=make_runtime(tmp_path)
    v.hr_request("export follow-up specialist")
    again=VanijyaSalesHead(tmp_path/"vanijya-sales.json")
    assert again.status()["counts"]["hr_requests"]==1
    assert again.health()["ok"] is True


def test_hr_request_create_and_retire_preserves_guardrails_and_learning(tmp_path):
    v=make_runtime(tmp_path)
    req=v.hr_request("multilingual export follow-up specialist",reason="Hindi and Odia follow-up")
    assert "zero_spend" in req["must_inherit"]
    assert "honor_opt_out" in req["must_inherit"]
    bot=v.hr_create_bot(req["request_id"],name="Export Follow-up Shishya",skills=["Hindi","Odia"])
    assert bot["reports_to"]=="rishi-vanijya"
    assert bot["status"]=="READY"
    assert "receive_only" in bot["guardrails"]
    retired=v.hr_retire_bot(bot["id"],outcome="campaign complete",lessons=["pricing question converts well"])
    assert retired["status"]=="RETIRED"
    assert retired["lessons"]==["pricing question converts well"]


def test_real_hr_plan_is_preapproved_by_krishna_and_workers_retire(tmp_path):
    v=make_runtime(tmp_path)
    workers=StubWorkerRuntime()
    v.bind_worker_runtime(workers)
    plan=v.hr_plan("Call qualified leads in Hindi",role_ids=["sdr-caller"],requested_count=2)
    req=plan["requests"][0]
    assert req["status"]=="approved"
    assert req["approved_by"]=="KRISHNA"
    assert req["manager"]=="rishi:vanijya"
    assert req["retention_policy"]=="findings_and_provenance_only"
    result=v.execute_hr_plan(
        "KRISHNA","Call qualified leads in Hindi",
        role_ids=["sdr-caller"],requested_count=2,privacy="local_only",
    )
    assert result["all_workers_retire_after_handover"] is True
    assert workers.requests[0]["request"]["approved_by"]=="KRISHNA"
    assert workers.requests[0]["privacy"]=="local_only"


def test_syncs_manibhadra_products_without_fabricating_products(tmp_path):
    products=[{"id":"p1","name":"Website Service","sale_price":15000,"source":"our product","status":"ready"}]
    v=make_runtime(tmp_path,products)
    out=v.sync_manibhadra_products()
    assert out["synced"]==1
    assert out["products"][0]["product_id"]=="p1"
    assert out["products"][0]["sale_price"]==15000
    assert v.sync_manibhadra_products()["synced"]==0


def test_sales_cycle_asks_manibhadra_when_no_product_exists(tmp_path):
    v=make_runtime(tmp_path,[])
    out=v.sales_cycle()
    assert out["status"]=="NEEDS_PRODUCT"
    assert out["next"]["to"]=="manibhadra"


def test_sales_cycle_uses_approved_manibhadra_product_and_all_agents(tmp_path):
    v=make_runtime(tmp_path,[{"id":"p1","name":"CRM Setup","sale_price":20000,"source":"our product","status":"ready"}])
    out=v.sales_cycle()
    assert out["status"]=="READY"
    assert out["product"]["name"]=="CRM Setup"
    assert [x["agent"] for x in out["workflow"]]==[x.id for x in PERMANENT_TEAM]
    assert out["zero_spend"] is True
    assert out["communications_via"]=="NARAD"


def test_autopilot_always_requests_manibhadra_and_assigns_sales_agents(tmp_path):
    products=[{"id":"p1","name":"Website Service","sale_price":15000,"source":"our product","status":"ready"}]
    crm=StubCRM(products)
    crm.records=lambda:{
        "products":products,
        "leads":[{"id":"l1","stage":"new","score":80,"next_action":"Call buyer"}],
        "deals":[{"id":"d1","stage":"negotiation","next_action":"Confirm terms"}],
        "tasks":[{"id":"t1","status":"open","priority":"high","title":"Follow up"}],
    }
    v=VanijyaSalesHead(tmp_path/"vanijya-sales.json",crm=crm)
    out=v.autopilot_plan()
    assert out["manibhadra_request"]["to"]=="manibhadra"
    assert out["external_send_performed"] is False
    assert out["spend_performed"] is False
    agents={x["agent"] for x in out["agent_queue"]}
    assert "lead-qualifier" in agents
    assert "deal-closer" in agents
    assert "relationship-manager" in agents


def test_campaign_is_zero_spend_and_paid_acquisition_disabled(tmp_path):
    v=make_runtime(tmp_path)
    c=v.create_campaign(
        {"id":"p1","name":"Website Service","sale_price":10000},
        channels=["gmail","whatsapp"],audience="retailers without websites",geography="Odisha",
    )
    assert c["status"]=="active"
    assert c["acquisition_cost_limit"]==0
    assert c["paid_ads"] is False
    assert c["paid_leads"] is False


def test_outreach_fails_closed_when_connector_missing():
    verdict=VanijyaSalesHead.outreach_decision(
        {"public_business_contact":True},channel="gmail",connector_state="WAITING_FOR_CONNECTION",
    )
    assert verdict["allowed"] is False
    assert "connector_not_connected" in verdict["reasons"]


def test_outreach_blocks_opt_out_and_private_unconsented_contact():
    opted=VanijyaSalesHead.outreach_decision(
        {"consented":True,"last_message":"Please unsubscribe me"},
        channel="email",connector_state="CONNECTED",
    )
    assert "opted_out" in opted["reasons"]
    private=VanijyaSalesHead.outreach_decision(
        {"email":"private@example.com"},channel="gmail",connector_state="CONNECTED",
    )
    assert private["allowed"] is False
    assert "no_public_or_consented_contact_basis" in private["reasons"]


def test_marketing_plan_requires_manibhadra_and_never_enables_paid_media(tmp_path):
    v=make_runtime(tmp_path)
    waiting=v.marketing_plan({"name":"CRM Service"},manibhadra_checked=False)
    assert waiting["status"]=="waiting_for_manibhadra"
    ready=v.marketing_plan({"name":"CRM Service"},manibhadra_checked=True)
    assert ready["paid_media"] is False
    assert ready["paid_leads"] is False
    assert ready["zero_spend"] is True


def test_whatsapp_public_number_alone_is_not_enough_for_automatic_promotion(tmp_path):
    v=make_runtime(tmp_path)
    plan=v.outreach_plan(
        "whatsapp",
        {
            "phone":"+911234567890",
            "contact_basis":"public_business_contact_for_relevant_b2b",
            "connector_state":"CONNECTED",
        },
        purpose="Product introduction",
        body="A truthful relevant business introduction.",
    )
    assert plan["can_enter_automatic_send_workflow"] is False
    assert "NARADA Legal" in plan["legal_gate"]


def test_lead_qualification_routes_only_real_fit_to_account_executive(tmp_path):
    v=make_runtime(tmp_path)
    q=v.qualify_lead(
        {"id":"lead1"},
        {"need":90,"fit":90,"engagement":80,"timing":70,"authority":60},
    )
    assert q["qualified"] is True
    assert q["next_agent"]=="account-executive"
    weak=v.qualify_lead({"id":"lead2"},{"need":20,"fit":20,"engagement":10})
    assert weak["qualified"] is False
    assert weak["stage"]=="nurture"


def test_customer_reply_is_recorded_and_pricing_routes_to_pricing_agent(tmp_path):
    messages=StubMessages()
    v=make_runtime(tmp_path,messages=messages)
    row=v.ingest_reply(
        lead_id="lead1",provider="gmail",sender="buyer@example.com",
        text="Please send the price and quotation",thread_ref="thread-1",
    )
    assert row["intent"]=="pricing"
    assert row["next"]["agent"]=="proposal-pricing"
    assert messages.rows[-1]["direction"]=="inbox"


def test_customer_opt_out_stops_marketing(tmp_path):
    v=make_runtime(tmp_path)
    row=v.ingest_reply(
        lead_id="lead1",provider="whatsapp",sender="+910000000000",
        text="Stop. Do not contact me again.",
    )
    assert row["intent"]=="opt_out"
    assert row["status"]=="opted_out"
    assert v.dashboard()["status"]["counts"]["conversations"]==1


def test_outbound_plan_records_narad_outbox_and_provider_payload(tmp_path):
    messages=StubMessages()
    v=make_runtime(tmp_path,messages=messages)
    lead={"id":"l1","email":"buyer@example.com","consented":True}
    out=v.plan_outbound(
        lead=lead,channel="gmail",connector_state="CONNECTED",
        subject="CRM proposal",text="Here is the requested information.",thread_ref="thread-1",
    )
    assert out["status"]=="queued"
    assert messages.rows[-1]["direction"]=="outbox"
    spec=v.provider_payload(out,lead)
    assert spec["provider"]=="gmail"
    assert spec["operation"]=="send_email"
    assert spec["payload"]["text"]=="Here is the requested information."
    assert spec["payload"]["thread_id"]=="thread-1"


def test_quote_uses_catalogue_price_and_rejects_unapproved_discount(tmp_path):
    v=make_runtime(tmp_path)
    product={"id":"p1","name":"Service","sale_price":"1000","approved_discount_percent":10}
    q=v.quote(lead_id="l1",product=product,quantity=2,approved_discount_percent=10)
    assert q["subtotal"]==2000.0
    assert q["amount_due"]==1800.0
    assert q["truth_source"]=="MANIBHADRA product record"
    with pytest.raises(PermissionError):
        v.quote(lead_id="l1",product=product,quantity=1,approved_discount_percent=20)


def test_exact_amount_upi_request_is_receive_only_and_persistent(tmp_path):
    v=make_runtime(tmp_path)
    req=v.upi_payment_request(
        payee_vpa="merchant@example",payee_name="Example Merchant",
        amount="1250",invoice_id="INV-1",deal_id="deal-1",lead_id="lead-1",
    )
    assert req["amount"]==1250.0
    assert req["receive_only"] is True
    assert "am=1250.00" in req["upi_uri"]
    assert req["status"]=="PENDING"
    assert v.status()["counts"]["pending_payments"]==1


def test_local_qr_renderer_is_optional_free_and_never_payment_proof(tmp_path):
    v=make_runtime(tmp_path)
    req=v.upi_payment_request(
        payee_vpa="merchant@example",payee_name="Example Merchant",
        amount="1250",invoice_id="INV-QR",
    )
    qr=v.payment_qr_svg(req)
    assert qr["payment_proof"] is False
    if qr["available"]:
        assert qr["mime_type"]=="image/svg+xml"
        assert qr["data_uri"].startswith("data:image/svg+xml;base64,")
    else:
        assert "INSTALL_KRISHNA_QR.ps1" in qr["install"]


def test_payment_screenshot_or_customer_claim_cannot_mark_paid(tmp_path):
    v=make_runtime(tmp_path)
    req=v.upi_payment_request(
        payee_vpa="merchant@example",payee_name="Example Merchant",
        amount="1250",invoice_id="INV-1",
    )
    result=v.verify_payment(req,{
        "provider":"customer_screenshot","source":"screenshot","signature_verified":False,"status":"SUCCESS",
        "invoice_id":"INV-1","amount":"1250","transaction_id":"claimed",
    })
    assert result["paid"] is False
    assert "unverified_evidence" in result["reasons"]
    assert v.status()["counts"]["paid_payments"]==0


def test_verified_provider_exact_payment_moves_linked_deal_to_won(tmp_path):
    crm=StubCRM()
    v=VanijyaSalesHead(tmp_path/"vanijya-sales.json",crm=crm)
    req=v.upi_payment_request(
        payee_vpa="merchant@example",payee_name="Example Merchant",
        amount="1250",invoice_id="INV-1",deal_id="deal-1",
    )
    result=v.verify_payment(req,{
        "provider":"gateway","source":"payment_gateway_webhook","signature_verified":True,"status":"CAPTURED",
        "invoice_id":"INV-1","amount":"1250","transaction_id":"pay_123",
    })
    assert result["paid"] is True
    assert result["status"]=="PAID"
    assert crm.moves==[("deal-1","won")]
    assert v.status()["counts"]["paid_payments"]==1


def test_pipeline_cannot_close_before_verified_payment_and_blueprint_preserves_boundaries(tmp_path):
    v=make_runtime(tmp_path)
    pending=v.pipeline_next("payment_pending",payment_verified=False)
    assert pending["stage"]=="payment_pending"
    assert v.pipeline_next("payment_pending",payment_verified=True)["stage"]=="won"
    blueprint=v.automation_blueprint()
    assert "NARAD" in " ".join(blueprint["product_loop"])
    assert any("outgoing money" in x for x in blueprint["never"])
