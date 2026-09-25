import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from krishna_core.hawkeye_ruview import HawkeyeRuViewBridge


class FakeVault:
    def __init__(self):
        self.values={}
        self.saved=[]
    def put(self,name,provider,secret):
        sid=f"s{len(self.saved)+1}"
        self.values[sid]=secret
        row={"id":sid,"name":name,"provider":provider,"backend":"fake"}
        self.saved.append((row,secret))
        return row
    def resolve(self,secret_id):
        return self.values[secret_id]


class FakeHawkeye:
    def __init__(self):
        self.rows=[]
    def record_lane(self,session_id,lane,payload,**kwargs):
        row={"session_id":session_id,"lane":lane,"payload":dict(payload),**kwargs}
        self.rows.append(row)
        return row


class HawkeyeRuViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.vault=FakeVault()
        self.hawkeye=FakeHawkeye()
        self.bridge=HawkeyeRuViewBridge(
            Path(self.tmp.name)/"ruview",
            secure_vault=self.vault,
            hawkeye=self.hawkeye,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_contract_keeps_wifi_credentials_pc_only(self):
        with patch.object(self.bridge,"wifi_status",return_value={
            "available":True,"connected":True,"ssid":"LabNet","signal_percent":81
        }):
            status=self.bridge.status(refresh=False)
        self.assertEqual(status["agent"],"HAWKEYE RUVIEW")
        self.assertEqual(status["mode"],"rssi_only")
        self.assertEqual(status["credentials"]["entry_surface"],"KRISHNA PC only")
        self.assertFalse(status["credentials"]["mobile_entry_allowed"])
        self.assertFalse(status["credentials"]["plaintext_returned"])
        self.assertIn("CSI",status["capability_limit"])

    def test_ruview_presence_and_pose_are_inferred_evidence(self):
        event={
            "type":"pose_data",
            "node_id":"esp32-1",
            "presence":True,
            "n_persons":2,
            "confidence":0.86,
            "persons":[{"keypoints":[{"x":0.3,"y":0.4}]}],
        }
        out=self.bridge.ingest_event("session-1",event)
        self.assertEqual(out["perception"]["lane"],"perception")
        self.assertEqual(out["perception"]["evidence_state"],"INFERRED")
        self.assertEqual(out["perception"]["payload"]["person_count"],2)
        self.assertEqual(out["perception"]["payload"]["modality"],"wifi_csi")
        self.assertIsNone(out["physio"])
        self.assertFalse(out["vitals_collected"])

    def test_vitals_are_off_by_default_even_if_ruview_emits_them(self):
        event={
            "type":"edge_vitals",
            "node_id":"esp32-2",
            "presence":True,
            "breathing_rate_bpm":14.2,
            "heartrate_bpm":72.0,
            "presence_score":0.9,
        }
        out=self.bridge.ingest_event("session-2",event)
        self.assertFalse(out["vitals_collected"])
        self.assertEqual(len(self.hawkeye.rows),1)
        self.assertEqual(self.hawkeye.rows[0]["lane"],"perception")
        self.assertNotIn("heartrate_bpm",self.hawkeye.rows[0]["payload"])

    def test_rssi_fallback_never_claims_pose_or_presence(self):
        with patch.object(self.bridge,"probe_ruview",return_value={"reachable":False}), \
             patch.object(self.bridge,"wifi_status",return_value={
                 "available":True,"connected":True,"ssid":"Home","signal_percent":67,"channel":"36"
             }):
            sample=self.bridge.sample("session-rssi")
        self.assertEqual(sample["mode"],"rssi_only")
        self.assertIn("cannot reconstruct body pose",sample["limitation"])
        row=sample["recorded"]
        self.assertEqual(row["evidence_state"],"MEASURED")
        self.assertEqual(row["payload"]["modality"],"wifi_rssi")
        self.assertIn("no person/pose inference",row["payload"]["observation"])

    def test_password_is_not_returned_and_persists_only_as_vault_reference(self):
        with patch.object(
            HawkeyeRuViewBridge,
            "_windows_set_profile_and_connect",
            return_value={"profile_written":True,"connect_requested":True,"interface":"Wi-Fi"},
        ), patch.object(self.bridge,"wifi_status",return_value={
            "available":True,"connected":True,"ssid":"SecureNet","signal_percent":90
        }):
            out=self.bridge.connect_wifi(
                ssid="SecureNet",password="not-for-logs",remember=True,wait_seconds=0
            )
        self.assertTrue(out["connected"])
        self.assertFalse(out["password_returned"])
        self.assertFalse(out["mobile_credential_entry"])
        self.assertNotIn("not-for-logs",str(out))
        self.assertEqual(len(self.vault.saved),1)
        self.assertEqual(self.vault.saved[0][1],"not-for-logs")
        self.assertEqual(out["secret_ref"]["provider"],"hawkeye-ruview-wifi")

    def test_profile_xml_escapes_special_characters(self):
        xml=self.bridge._profile_xml('A&B','x<y&z','WPA2PSK','AES')
        self.assertIn("A&amp;B",xml)
        self.assertIn("x&lt;y&amp;z",xml)
        self.assertNotIn("<keyMaterial>x<y&z</keyMaterial>",xml)


if __name__=="__main__":
    unittest.main()
