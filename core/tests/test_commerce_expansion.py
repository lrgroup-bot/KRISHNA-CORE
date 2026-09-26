from krishna_core.commerce_expansion import CommerceExpansionRegistry


def test_registry_contains_every_handoff_expansion():
    reg=CommerceExpansionRegistry()
    ids={x["id"] for x in reg.list()}
    assert ids=={
        "ondc","ebay","etsy","google_merchant_free","google_search_console",
        "pinterest_shopping","organic_social","supplier_funded_dropshipping",
        "b2b_rfq","importer_distributor_discovery","ai_commerce_ucp","medusa",
    }
    assert reg.status()["zero_spend"] is True
    assert reg.status()["paid_fallback"] is False


def test_external_writes_fail_closed_without_connection_and_free_verification():
    reg=CommerceExpansionRegistry()
    out=reg.plan("google_merchant_free",connected=False,free_verified=False)
    assert out["external_write_allowed"] is False
    assert "WAITING_FOR_CONNECTION" in out["blockers"]
    assert "FREE_ROUTE_NOT_VERIFIED" in out["blockers"]


def test_verified_free_connected_route_can_become_write_ready():
    out=CommerceExpansionRegistry().plan(
        "google_merchant_free",connected=True,free_verified=True,
    )
    assert out["external_write_allowed"] is True
    assert out["zero_spend"] is True


def test_etsy_fee_route_remains_blocked_even_when_connected():
    out=CommerceExpansionRegistry().plan("etsy",connected=True,free_verified=True)
    assert out["external_write_allowed"] is False
    assert "OUTGOING_COST_PATH_BLOCKED" in out["blockers"]


def test_medusa_is_local_self_hosted_candidate_not_paid_hosting_authority():
    row=CommerceExpansionRegistry().get("medusa")
    assert row["owner"]=="MANIBHADRA"
    assert "NO_PAID_HOSTING" in row["zero_spend_status"]
