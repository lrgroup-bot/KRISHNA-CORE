from krishna_core.vanijya_sales import VanijyaSalesHead, PERMANENT_TEAM


def test_vanijya_is_independent_sales_marketing_head():
    v = VanijyaSalesHead()
    status = v.status()
    assert status["independent"] is True
    assert status["title"] == "Independent Sales & Marketing Head"
    assert status["asks_manibhadra_for_products"] is True
    assert len(PERMANENT_TEAM) == 8


def test_hr_request_inherits_guardrails():
    row = VanijyaSalesHead().hr_request("multilingual export follow-up specialist")
    assert row["status"] == "REQUESTED"
    assert "zero_spend" in row["must_inherit"]
    assert "honor_opt_out" in row["must_inherit"]


def test_outreach_fails_closed_when_connector_missing():
    verdict = VanijyaSalesHead.outreach_decision(
        {"public_business_contact": True},
        channel="gmail",
        connector_state="WAITING_FOR_CONNECTION",
    )
    assert verdict["allowed"] is False
    assert "connector_not_connected" in verdict["reasons"]


def test_outreach_blocks_opt_out():
    verdict = VanijyaSalesHead.outreach_decision(
        {"consented": True, "last_message": "Please unsubscribe me"},
        channel="email",
        connector_state="CONNECTED",
    )
    assert verdict["allowed"] is False
    assert "opted_out" in verdict["reasons"]


def test_exact_amount_upi_request_is_receive_only():
    req = VanijyaSalesHead.upi_payment_request(
        payee_vpa="merchant@example",
        payee_name="Example Merchant",
        amount="1250",
        invoice_id="INV-1",
    )
    assert req["amount"] == 1250.0
    assert req["receive_only"] is True
    assert "am=1250.00" in req["upi_uri"]
    assert req["status"] == "PENDING"


def test_payment_screenshot_or_customer_claim_cannot_mark_paid():
    req = VanijyaSalesHead.upi_payment_request(
        payee_vpa="merchant@example",
        payee_name="Example Merchant",
        amount="1250",
        invoice_id="INV-1",
    )
    result = VanijyaSalesHead.verify_payment(
        req,
        {
            "provider": "customer_screenshot",
            "signature_verified": False,
            "status": "SUCCESS",
            "invoice_id": "INV-1",
            "amount": "1250",
            "transaction_id": "claimed",
        },
    )
    assert result["paid"] is False
    assert "unverified_evidence" in result["reasons"]


def test_verified_provider_exact_payment_can_mark_paid():
    req = VanijyaSalesHead.upi_payment_request(
        payee_vpa="merchant@example",
        payee_name="Example Merchant",
        amount="1250",
        invoice_id="INV-1",
    )
    result = VanijyaSalesHead.verify_payment(
        req,
        {
            "provider": "trusted_psp",
            "signature_verified": True,
            "status": "CAPTURED",
            "invoice_id": "INV-1",
            "amount": "1250",
            "transaction_id": "pay_123",
        },
    )
    assert result["paid"] is True
    assert result["status"] == "PAID"
