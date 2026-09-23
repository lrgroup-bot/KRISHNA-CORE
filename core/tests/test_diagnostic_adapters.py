import math
import unittest

from krishna_core.diagnostic_adapters import (
    AcousticMeasurementAdapter,
    DiagnosticAdapterRegistry,
    ElectronicsMeasurementAdapter,
    VehicleReadOnlyAdapter,
)


class DiagnosticAdapterTests(unittest.TestCase):
    def test_electronics_measurements_are_structured_and_hazard_bounded(self):
        adapter=ElectronicsMeasurementAdapter()
        out=adapter.ingest([
            {"point":"TP1","quantity":"voltage","value":12.2,"unit":"V"},
            {"point":"R10","quantity":"resistance","value":4.7,"unit":"kohm"},
        ],source="multimeter")
        self.assertEqual(out["evidence_state"],"MEASURED")
        self.assertFalse(out["hazardous_voltage_possible"])
        self.assertFalse(out["safety"]["controls_instrument"])
        hv=adapter.ingest([
            {"point":"DC_BUS","quantity":"voltage","value":400,"unit":"V"}
        ],source="multimeter")
        self.assertTrue(hv["hazardous_voltage_possible"])
        self.assertFalse(hv["safety"]["high_voltage_probe_authorized"])

    def test_vehicle_adapter_decodes_common_obd_pids_read_only(self):
        adapter=VehicleReadOnlyAdapter()
        out=adapter.ingest("obd2",[
            {"mode":1,"pid":0x0C,"data":[0x1A,0xF8],"direction":"rx"},
            {"mode":1,"pid":0x0D,"data":[88],"direction":"rx"},
            {"mode":1,"pid":0x05,"data":[90],"direction":"rx"},
        ])
        self.assertEqual(out["frames"][0]["name"],"engine_rpm")
        self.assertEqual(out["frames"][0]["value"],1726.0)
        self.assertEqual(out["frames"][1]["value"],88.0)
        self.assertEqual(out["frames"][2]["value"],50.0)
        self.assertTrue(out["safety"]["read_only"])
        self.assertFalse(out["safety"]["transmit"])

    def test_vehicle_adapter_rejects_transmit_program_or_control(self):
        adapter=VehicleReadOnlyAdapter()
        for action in ("transmit","write","program","flash","control","actuate"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionError):
                    adapter.ingest("can",[{
                        "can_id":0x123,"data":[1,2,3],"action":action
                    }])

    def test_j1939_extracts_pgn_without_claiming_spn_decode(self):
        adapter=VehicleReadOnlyAdapter()
        # 0x0CF00401 -> EEC1 PGN 0xF004 from source address 0x01.
        out=adapter.ingest("j1939",[{
            "can_id":0x0CF00401,"data":[0,1,2,3,4,5,6,7]
        }])
        row=out["frames"][0]
        self.assertEqual(row["pgn"],0xF004)
        self.assertEqual(row["source_address"],0x01)
        self.assertEqual(row["spn_decode"],"reference_required")

    def test_acoustic_adapter_extracts_features_without_raw_retention(self):
        adapter=AcousticMeasurementAdapter()
        rate=8000
        samples=[math.sin(2*math.pi*400*i/rate) for i in range(800)]
        out=adapter.ingest(samples,rate,source="microphone")
        self.assertEqual(out["evidence_state"],"MEASURED")
        self.assertFalse(out["raw_samples_retained"])
        self.assertGreater(out["features"]["rms"],0.6)
        freqs=[x["frequency_hz"] for x in out["features"]["dominant_frequencies"]]
        self.assertTrue(any(abs(f-400)<30 for f in freqs))

    def test_registry_states_hardware_boundaries_explicitly(self):
        status=DiagnosticAdapterRegistry().status()
        self.assertEqual(status["version"],"diagnostic-adapters-v1")
        self.assertEqual(status["electronics"]["hardware_transport"],"adapter_required")
        self.assertEqual(status["vehicle"]["transport"],"hardware_interface_required")
        self.assertEqual(status["acoustic"]["capture_transport"],"microphone_or_sensor_adapter_required")
        self.assertIn("retest",status["verification_rule"])


if __name__=="__main__":
    unittest.main()
