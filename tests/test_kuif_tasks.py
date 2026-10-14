import pytest
from kuif.tasks import State, Task

def test_task_lifecycle():
    task = Task("t1", "krishna")
    task.transition(State.RUNNING)
    task.transition(State.SUCCEEDED)
    with pytest.raises(ValueError):
        task.transition(State.RUNNING)

def test_invalid_initial_transition():
    with pytest.raises(ValueError):
        Task("t2", "krishna").transition(State.SUCCEEDED)
