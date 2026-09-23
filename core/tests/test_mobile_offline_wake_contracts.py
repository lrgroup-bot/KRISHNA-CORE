import os
import unittest
from pathlib import Path


def repository_root():
    configured=str(os.environ.get("KRISHNA_SOURCE_ROOT") or "").strip()
    return Path(configured).resolve() if configured else Path(__file__).resolve().parents[2]


class MobileOfflineWakeContracts(unittest.TestCase):
    def test_offline_probe_is_local_non_semantic_and_persisted_before_sync(self):
        root=repository_root()
        probe=(root/"mobile_v3"/"HawkeyeOfflinePerception.java").read_text(encoding="utf-8")
        main=(root/"mobile_v3"/"MainActivity.java").read_text(encoding="utf-8")
        self.assertIn("ANDROID_LOCAL_LIGHTWEIGHT_PROBE",probe)
        self.assertIn('out.put("pc_required",false)',probe)
        self.assertIn('out.put("semantic_model_configured",false)',probe)
        self.assertIn("HawkeyeOfflinePerception.analyze",main)
        self.assertIn("HawkeyeEdgeMemory.rememberMedia",main)
        self.assertIn('sensors.put("offline_perception",local)',main)

    def test_wake_service_is_local_activation_not_authentication(self):
        root=repository_root()
        wake=(root/"mobile_v3"/"KrishnaWakeService.java").read_text(encoding="utf-8")
        main=(root/"mobile_v3"/"MainActivity.java").read_text(encoding="utf-8")
        workflow=(root/".github"/"workflows"/"build-mobile-v3.yml").read_text(encoding="utf-8")
        self.assertIn("createOnDeviceSpeechRecognizer",wake)
        self.assertIn('o.put("local_only",true)',wake)
        self.assertIn('o.put("wake_is_authentication",false)',wake)
        self.assertIn("voiceprint",main)
        self.assertIn("startWakeIfReady",main)
        self.assertIn("Context.RECEIVER_NOT_EXPORTED",main)
        self.assertIn("FOREGROUND_SERVICE_MICROPHONE",workflow)
        self.assertIn('android:foregroundServiceType="microphone"',workflow)


if __name__=="__main__":
    unittest.main()
