import unittest

from kuif.tasks import State, Task


class KuifTaskTests(unittest.TestCase):
    def test_task_lifecycle(self):
        task = Task("t1", "krishna")
        task.transition(State.RUNNING)
        task.transition(State.SUCCEEDED)
        with self.assertRaises(ValueError):
            task.transition(State.RUNNING)

    def test_invalid_initial_transition(self):
        with self.assertRaises(ValueError):
            Task("t2", "krishna").transition(State.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
