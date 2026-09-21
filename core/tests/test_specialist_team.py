import unittest
from krishna_core.specialist_team import SpecialistTeamPlanner

class Agency:
    def select(self,task,limit):
        return [{"id":"engineering/example","name":"Example Engineer","division":"engineering","description":"advisory"}]

class SpecialistTeamPlannerTests(unittest.TestCase):
    def test_team_always_has_critic_and_independent_verifier(self):
        p=SpecialistTeamPlanner(Agency())
        team=p.plan("Fix backend API error and test it","KRISHNA")
        roles={x["role"] for x in team["roles"]}
        self.assertIn("backend",roles)
        self.assertIn("debugger",roles)
        self.assertIn("testing",roles)
        self.assertIn("critic",roles)
        self.assertIn("verifier",roles)
        self.assertFalse(team["live_mutation_allowed"])
        verifier=next(x for x in team["roles"] if x["role"]=="verifier")
        self.assertIn("backend",verifier["independent_from"])

    def test_security_task_is_advisory_not_live_mutation(self):
        team=SpecialistTeamPlanner().plan("Review authentication secret permissions","KRISHNA")
        security=next(x for x in team["roles"] if x["role"]=="security")
        self.assertFalse(security["can_mutate_live"])
        self.assertIn("security.inspect",security["permissions"])

    def test_blank_task_rejected(self):
        with self.assertRaises(ValueError):SpecialistTeamPlanner().plan("")

if __name__=="__main__": unittest.main()
