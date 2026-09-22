import unittest
from dataclasses import asdict

from krishna_core.garuda import GarudaAgent, WebCandidate


class MemoryStub:
    def __init__(self):
        self.rows=[]
        self.audit_rows=[]
    def remember(self,*args):
        self.rows.append(args)
    def audit(self,*args):
        self.audit_rows.append(args)


class GitHubStub:
    def search(self,*args,**kwargs):
        return {"candidates":[]}


class ScienceGarudaStub(GarudaAgent):
    def __init__(self):
        super().__init__(GitHubStub(),MemoryStub())
        self.called=[]
    def scout(self,project,goal,limit=10):
        return {
            "agent":"Garuda","role":"research_and_evidence","project":project,"goal":goal,
            "web":[asdict(WebCandidate("Base paper","https://example.org/base","base evidence","arxiv",2,False,"basefp"))],
            "github":[],"errors":{},"coverage":["public_web","research_papers"],
        }
    def _openalex(self,query,limit=10):
        self.called.append("openalex")
        return [WebCandidate("OpenAlex work","https://openalex.org/W1","scholarly metadata","openalex",5)]
    def _crossref(self,query,limit=10):
        self.called.append("crossref")
        return [WebCandidate("Crossref work","https://doi.org/10.1/x","publisher metadata","crossref",4)]
    def _europe_pmc(self,query,limit=10):
        self.called.append("europepmc")
        return [WebCandidate("Europe PMC paper","https://europepmc.org/article/MED/1","biomedical abstract","europepmc",6)]
    def _clinical_trials(self,query,limit=10):
        self.called.append("clinicaltrials")
        return [WebCandidate("Clinical trial","https://clinicaltrials.gov/study/NCT1","registered study","clinicaltrials",6)]


class GarudaScienceSourceTests(unittest.TestCase):
    def test_biomedical_research_adds_biomedical_and_clinical_indexes(self):
        g=ScienceGarudaStub()
        out=g.science_scout("KRISHNA","DNA aging cancer therapy",5)
        self.assertEqual(set(g.called),{"openalex","crossref","europepmc","clinicaltrials"})
        coverage=set(out["coverage"])
        for name in ("openalex","crossref","europepmc","clinicaltrials"):
            self.assertIn(name,coverage)
        sources={x["source"] for x in out["web"]}
        self.assertIn("europepmc",sources)
        self.assertIn("clinicaltrials",sources)
        self.assertTrue(out["science_protocol"]["source_independence_required"])
        self.assertTrue(out["science_protocol"]["clinical_trial_registration_not_equivalent_to_positive_result"])

    def test_non_biomedical_science_avoids_irrelevant_clinical_calls(self):
        g=ScienceGarudaStub()
        out=g.science_scout("KRISHNA","quantum materials superconductivity",5)
        self.assertEqual(set(g.called),{"openalex","crossref"})
        self.assertNotIn("europepmc",out["coverage"])
        self.assertNotIn("clinicaltrials",out["coverage"])

    def test_biomedical_detection_covers_genetics_neuroscience_and_pharmacology(self):
        self.assertTrue(GarudaAgent._looks_biomedical("genetic genome therapy"))
        self.assertTrue(GarudaAgent._looks_biomedical("neural brain disease"))
        self.assertTrue(GarudaAgent._looks_biomedical("drug pharmacology patient"))
        self.assertFalse(GarudaAgent._looks_biomedical("stellar cosmology black holes"))

    def test_scholarly_sources_rank_above_general_web(self):
        self.assertGreater(GarudaAgent._source_weight("clinicaltrials"),GarudaAgent._source_weight("web"))
        self.assertGreater(GarudaAgent._source_weight("europepmc"),GarudaAgent._source_weight("arxiv"))
        self.assertGreater(GarudaAgent._source_weight("openalex"),GarudaAgent._source_weight("hackernews"))

    def test_science_scout_preserves_base_discovery_and_deduplicates(self):
        g=ScienceGarudaStub()
        out=g.science_scout("KRISHNA","materials engineering",5)
        titles=[x["title"] for x in out["web"]]
        self.assertIn("Base paper",titles)
        self.assertIn("OpenAlex work",titles)
        self.assertIn("Crossref work",titles)
        self.assertEqual(len(titles),len(set((x["url"],x["title"]) for x in out["web"])))


if __name__=="__main__":
    unittest.main()
