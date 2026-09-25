import time
import unittest
from pathlib import Path
import tempfile

from krishna_core.mrityunjay import MrityunjayRuntime


class _Bus:
    def __init__(self):
        self.handlers = {}
    def subscribe(self, topic, handler):
        self.handlers.setdefault(topic, []).append(handler)
    def unsubscribe(self, topic, handler):
        if handler in self.handlers.get(topic, []):
            self.handlers[topic].remove(handler)


class MrityunjayTests(unittest.TestCase):
    def test_status_declares_bounded_autonomous_scope(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = MrityunjayRuntime(Path(td), _Bus(), enabled=True)
            status = runtime.status()
            self.assertEqual(status["name"], "MRITYUNJAY")
            self.assertTrue(status["enabled"])
            self.assertIn("credentials/secrets", status["blocked_scope"])
            self.assertIn("transactional promotion", status["promotion_rule"])

    def test_attach_subscribes_to_failure_events(self):
        with tempfile.TemporaryDirectory() as td:
            bus = _Bus()
            runtime = MrityunjayRuntime(Path(td), bus, enabled=True)
            runtime.bind(lambda **kwargs: {"status": "healthy", "verified": True})
            runtime.attach()
            for topic in runtime.TRIGGERS:
                self.assertIn(runtime._on_event, bus.handlers.get(topic, []))

    def test_self_heal_failure_events_do_not_recurse(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = MrityunjayRuntime(Path(td), _Bus(), enabled=True)
            calls = []
            runtime.bind(lambda **kwargs: calls.append(kwargs) or {"status": "healthy", "verified": True})
            out = runtime._on_event({
                "topic": "action.failed",
                "payload": {"project": "KRISHNA", "action": "self_heal.run", "actor": "owner"},
            })
            self.assertFalse(out["scheduled"])
            self.assertEqual(calls, [])

    def test_runtime_failure_schedules_one_bounded_heal(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = MrityunjayRuntime(Path(td), _Bus(), enabled=True, cooldown_seconds=60)
            calls = []
            def heal(**kwargs):
                calls.append(kwargs)
                return {"status": "healthy", "verified": True}
            runtime.bind(heal)
            out = runtime._on_event({
                "topic": "TEST_FAILED",
                "created_at": time.time(),
                "payload": {"project": "KRISHNA", "reason": "unit regression"},
            })
            self.assertTrue(out["scheduled"])
            deadline = time.time() + 2
            while not calls and time.time() < deadline:
                time.sleep(0.01)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["project"], "KRISHNA")
            self.assertIn("TEST_FAILED", calls[0]["reason"])

            again = runtime._on_event({
                "topic": "TEST_FAILED",
                "payload": {"project": "KRISHNA", "reason": "same regression"},
            })
            self.assertFalse(again["scheduled"])
            self.assertIn(again["reason"], {"cooldown", "busy"})

    def test_orchestrator_contract_registers_mrityunjay_actions_and_agent(self):
        source=(Path(__file__).resolve().parents[1]/"krishna_core"/"orchestrator.py").read_text(encoding="utf-8")
        for token in (
            '"mrityunjay.status"',
            '"mrityunjay.heal"',
            '"mrityunjay","autonomous bounded self-heal',
            "self.mrityunjay.bind(self._mrityunjay_heal_event)",
            "self.mrityunjay.attach()",
            '"auto_apply":True',
        ):
            self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
