"""Expert attribution metadata is evidence, never a fake authentication badge."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from suryadev_source_authority import (valid_orcid, corroborate_scholarly_author,
                                       crossref_metadata)


class ScholarlyAttributionTests(unittest.TestCase):
    def test_orcid_checksum_and_doi_author_metadata(self):
        ident="0000-0002-1825-0097"
        self.assertTrue(valid_orcid(ident))
        self.assertFalse(valid_orcid("0000-0002-1825-0090"))
        md={"message":{"DOI":"10.5555/abc-2026",
                       "author":[{"given":"Alice","family":"Example",
                                  "ORCID":"https://orcid.org/"+ident}]}}
        receipt=corroborate_scholarly_author(
            doi="10.5555/abc-2026",orcid=ident,
            person_name="Alice Example",metadata=md)
        self.assertTrue(receipt["scholarly_attribution_correlated"])
        self.assertFalse(receipt["human_identity_authenticated"])
        self.assertFalse(receipt["video_speaker_identity_authenticated"])
        self.assertTrue(receipt["institutional_profile_review_required"])

    def test_wrong_author_fails_closed_and_metadata_is_not_self_authentication(self):
        ident="0000-0002-1825-0097"
        receipt=corroborate_scholarly_author(
            doi="10.5555/abc-2026",orcid=ident,person_name="Bob Example",
            metadata={"message":{"DOI":"10.5555/abc-2026",
               "author":[{"given":"Alice","family":"Example",
                          "ORCID":"https://orcid.org/"+ident}]}})
        self.assertFalse(receipt["scholarly_attribution_correlated"])
        self.assertFalse(receipt["human_identity_authenticated"])

    def test_bad_identifiers_refused_before_any_network(self):
        with patch("suryadev_source_authority.crossref_metadata") as remote:
            for doi in ("http://127.0.0.1/","INVALID","10.11/b"):
                with self.assertRaises(ValueError):
                    corroborate_scholarly_author(
                        doi=doi,orcid="0000-0002-1825-0097",person_name="Alice Example")
            with self.assertRaises(ValueError):
                corroborate_scholarly_author(
                    doi="10.5555/abc-2026",orcid="not-an-orcid",person_name="Alice Example")
            remote.assert_not_called()


if __name__ == "__main__":
    unittest.main()
