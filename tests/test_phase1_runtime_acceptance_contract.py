import unittest
from pathlib import Path


class Phase1RuntimeAcceptanceContractTests(unittest.TestCase):
    def test_acceptance_validates_durable_mission_queue_authority(self):
        root=Path(__file__).resolve().parents[1]
        script=(root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        for token in (
            'durable-queue-inline-worker',
            'KRISHNA Durable Queue',
            'pending == 0 AND processing == 0',
            'KRISHNA Mission Engine',
            '/api/missions/status',
            '/api/queue/status',
            '/api/protocol',
            'mission_id',
            'queue_id',
            'COMPLETED',
        ):
            self.assertIn(token,script)

    def test_acceptance_no_longer_requires_legacy_taskledger_authority_text(self):
        root=Path(__file__).resolve().parents[1]
        script=(root/"scripts"/"ACCEPT_KRISHNA_RUNTIME.ps1").read_text(encoding="utf-8")
        self.assertNotIn('Durable TaskLedger-backed jobs use Shared Action Bus',script)


if __name__=="__main__":
    unittest.main()
