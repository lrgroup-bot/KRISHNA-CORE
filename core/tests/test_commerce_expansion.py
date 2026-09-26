import unittest

from krishna_core.commerce_expansion import CommerceExpansionRegistry


class CommerceExpansionTests(unittest.TestCase):
    def test_registry_contains_every_handoff_expansion(self):
        reg=CommerceExpansionRegistry()
        ids={x["id"] for x in reg.list()}
        self.assertEqual(ids,{
            "ondc","ebay","etsy","google_merchant_free","google_search_console",
            "pinterest_shopping","organic_social","supplier_funded_dropshipping",
            "b2b_rfq","importer_distributor_discovery","ai_commerce_ucp","medusa",
        })
        self.assertTrue(reg.status()["zero_spend"])
        self.assertFalse(reg.status()["paid_fallback"])

    def test_external_writes_fail_closed_without_connection_and_free_verification(self):
        out=CommerceExpansionRegistry().plan("google_merchant_free",connected=False,free_verified=False)
        self.assertFalse(out["external_write_allowed"])
        self.assertIn("WAITING_FOR_CONNECTION",out["blockers"])
        self.assertIn("FREE_ROUTE_NOT_VERIFIED",out["blockers"])

    def test_verified_free_connected_route_can_become_write_ready(self):
        out=CommerceExpansionRegistry().plan("google_merchant_free",connected=True,free_verified=True)
        self.assertTrue(out["external_write_allowed"])
        self.assertTrue(out["zero_spend"])

    def test_etsy_fee_route_remains_blocked_even_when_connected(self):
        out=CommerceExpansionRegistry().plan("etsy",connected=True,free_verified=True)
        self.assertFalse(out["external_write_allowed"])
        self.assertIn("OUTGOING_COST_PATH_BLOCKED",out["blockers"])

    def test_medusa_is_local_self_hosted_candidate_not_paid_hosting_authority(self):
        row=CommerceExpansionRegistry().get("medusa")
        self.assertEqual(row["owner"],"MANIBHADRA")
        self.assertIn("NO_PAID_HOSTING",row["zero_spend_status"])


if __name__=="__main__":
    unittest.main()
