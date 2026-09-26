import tempfile
import unittest

from krishna_core.engineering_swarm import EngineeringSwarmManager


class FakeMissionEngine:
    def __init__(self):
        self.rows=[]
        self.cancelled=[]
    def create(self, goal, **kwargs):
        row={"mission_id":f"m{len(self.rows)+1}","goal":goal,**kwargs}
        self.rows.append(row)
        return row
    def transition(self, mission_id, status, error=None):
        self.cancelled.append((mission_id,status,error))
        return {"mission_id":mission_id,"status":status}


class FakeWorktrees:
    def __init__(self):
        self.created=[]
        self.removed=[]
    def create(self, project, worker_id, **kwargs):
        row={"project":project,"worker_id":worker_id,"path":f"/tmp/{project}-{worker_id}","branch":f"krishna/{project}/{worker_id}"}
        self.created.append(row)
        return row
    def remove(self, path, **kwargs):
        self.removed.append(path)
        return {"removed":True}


class EngineeringSwarmTests(unittest.TestCase):
    def test_staffing_creates_child_missions_and_worktrees_only_for_mutating_tasks(self):
        with tempfile.TemporaryDirectory() as td:
            manager=EngineeringSwarmManager(td)
            missions=FakeMissionEngine(); worktrees=FakeWorktrees()
            plan={
                "tasks":[
                    {"id":"backend","role":"backend","mutable":True,"depends_on":[]},
                    {"id":"security","role":"security","mutable":False,"depends_on":["backend"]},
                ],
                "dependency_waves":[
                    {"wave":1,"batches":[[{"id":"backend","execution_host":"registered_project_host","reasoning_route":{"reasoning":"local_ollama"},"worktree_required":True}]]},
                    {"wave":2,"batches":[[{"id":"security","execution_host":"registered_project_host","reasoning_route":{"reasoning":"local_ollama"},"worktree_required":False}]]},
                ],
                "recommended_workers":2,
                "local_execution_slots":2,
                "deadline_risk":False,
            }
            out=manager.staff("demo",plan,parent_mission_id="parent-1",mission_engine=missions,worktree_manager=worktrees)
            self.assertEqual(out["status"],"STAFFED")
            self.assertEqual(len(missions.rows),2)
            self.assertEqual(len(worktrees.created),1)
            backend=next(x for x in out["workers"] if x["task_id"]=="backend")
            security=next(x for x in out["workers"] if x["task_id"]=="security")
            self.assertIsNotNone(backend["worktree"])
            self.assertIsNone(security["worktree"])
            self.assertTrue(out["policy"]["hr_defines_staffing"])

    def test_staff_is_idempotent_for_same_parent_mission(self):
        with tempfile.TemporaryDirectory() as td:
            manager=EngineeringSwarmManager(td)
            missions=FakeMissionEngine(); worktrees=FakeWorktrees()
            plan={"tasks":[{"id":"a","role":"backend","mutable":False}],"dependency_waves":[{"wave":1,"batches":[[{"id":"a"}]]}]}
            first=manager.staff("demo",plan,parent_mission_id="p",mission_engine=missions,worktree_manager=worktrees)
            second=manager.staff("demo",plan,parent_mission_id="p",mission_engine=missions,worktree_manager=worktrees)
            self.assertEqual(first,second)
            self.assertEqual(len(missions.rows),1)


if __name__=="__main__":
    unittest.main()
