"""In-memory task state machine; not durable across process restarts."""
from dataclasses import dataclass
from enum import Enum

class State(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

@dataclass
class Task:
    task_id: str
    project: str
    state: State = State.QUEUED

    def transition(self, next_state: State) -> None:
        allowed = {State.QUEUED: {State.RUNNING, State.FAILED},
                   State.RUNNING: {State.SUCCEEDED, State.FAILED}}
        if next_state not in allowed.get(self.state, set()):
            raise ValueError("Invalid task state transition")
        self.state = next_state
