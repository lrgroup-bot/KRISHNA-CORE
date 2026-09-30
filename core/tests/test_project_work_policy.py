import unittest
from krishna_core.project_work_policy import ProjectWorkPolicy
from krishna_core.github_validation_policy import GitHubValidationPolicy

class ProjectWorkPolicyTests(unittest.TestCase):
 def test_research_external_build_local(self):
  p=ProjectWorkPolicy()
  self.assertEqual(p.route("web_research")["primary"],"web+github-research")
  self.assertEqual(p.route("frontend")["privacy"],"local_only")
  self.assertEqual(p.route("backend")["privacy"],"local_only")
 def test_cloud_only_after_failure_and_free_proof(self):
  p=ProjectWorkPolicy()
  self.assertFalse(p.route("coding")["cloud_allowed"])
  self.assertFalse(p.route("coding",local_failed=True)["cloud_allowed"])
  self.assertTrue(p.route("coding",local_failed=True,free_cloud_verified=True)["cloud_allowed"])
 def test_sensitive_never_cloud(self):
  p=ProjectWorkPolicy()
  self.assertFalse(p.route("coding",sensitive=True,local_failed=True,free_cloud_verified=True)["cloud_allowed"])
  with self.assertRaises(PermissionError):p.cloud_escalation_packet(problem="x",sensitive=True)
 def test_github_zero_spend_gate(self):
  g=GitHubValidationPolicy()
  self.assertTrue(g.decide(repo_visibility="public",runner="github-hosted")["allowed"])
  self.assertFalse(g.decide(repo_visibility="private",runner="github-hosted")["allowed"])
  self.assertTrue(g.decide(repo_visibility="private",runner="github-hosted",zero_cost_proven=True)["allowed"])
  self.assertFalse(g.decide(repo_visibility="private",runner="self-hosted",isolated=False,trusted=True)["allowed"])
  self.assertTrue(g.decide(repo_visibility="private",runner="self-hosted",isolated=True,trusted=True)["allowed"])
if __name__=="__main__":unittest.main()
