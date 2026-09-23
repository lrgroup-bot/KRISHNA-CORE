import math
import unittest

from krishna_core.quantum_nano_lab import QuantumNanoLab


class QuantumNanoLabTests(unittest.TestCase):
    def setUp(self):
        self.lab=QuantumNanoLab()

    def test_bell_state_local_statevector(self):
        result=self.lab.quantum_simulate({
            "qubits":2,
            "gates":[
                {"gate":"h","target":0},
                {"gate":"cx","control":0,"target":1},
            ],
        })
        self.assertFalse(result["physical"])
        self.assertAlmostEqual(result["probabilities"]["00"],0.5,places=10)
        self.assertAlmostEqual(result["probabilities"]["11"],0.5,places=10)
        self.assertAlmostEqual(result["normalization"],1.0,places=10)

    def test_quantum_plan_requires_classical_baseline_and_no_advantage_claim(self):
        plan=self.lab.quantum_plan({"question":"Can a quantum sensing model improve magnetic field estimation?"})
        self.assertIn("classical baseline",plan["tracks"])
        self.assertIn("quantum sensing model",plan["tracks"])
        self.assertFalse(plan["providers"]["real_qpu_verified"])
        self.assertTrue(any("quantum advantage" in x for x in plan["evidence_rules"]))

    def test_nano_sphere_surface_to_volume(self):
        result=self.lab.nano_geometry({"shape":"sphere","radius_nm":5})
        self.assertFalse(result["physical"])
        self.assertAlmostEqual(result["surface_to_volume_per_nm"],3/5,places=10)
        self.assertGreater(result["surface_area_nm2"],0)
        self.assertGreater(result["volume_nm3"],0)

    def test_nano_plan_marks_fabrication_unverified(self):
        plan=self.lab.nano_plan({"objective":"Study optical response of a nanoscale semiconductor surface"})
        self.assertIn("optical-property workflow",plan["analyses"])
        self.assertFalse(plan["providers"]["nanofabrication_verified"])

    def test_quantum_nano_bridge_targets_intersection(self):
        plan=self.lab.bridge_plan({"objective":"Explore a nanoscale quantum sensor"})
        self.assertIn("nanoscale quantum sensors",plan["candidate_areas"])
        self.assertFalse(plan["physical_execution"])

    def test_status_separates_software_from_real_hardware(self):
        status=self.lab.status()
        self.assertTrue(status["quantum"]["local_statevector"])
        self.assertFalse(status["quantum"]["real_qpu_verified"])
        self.assertFalse(status["nano"]["nanofabrication_verified"])


if __name__=="__main__":
    unittest.main()
