"""Independent CHANDRADEV watch state is durable and never controls PCs."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"standalone"/"chandradev"))
from fleet_watch import ChandradevFleetWatch, load_config, SCHEMA

class FleetWatchTests(unittest.TestCase):
    def test_transition_log_and_restart_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            reports=[
                {"nodes":[{"device_id":"suryadev-01","state":"healthy"}],"alerts":0},
                {"nodes":[{"device_id":"suryadev-01","state":"critical"}],"alerts":1},
                {"nodes":[{"device_id":"suryadev-01","state":"critical"}],"alerts":1}]
            def feed(config):
                return reports.pop(0)
            watch=ChandradevFleetWatch(folder,{"device_id":"chandradev-01"},
                                      transport=feed,clock=lambda:1000.0)
            a=watch.tick();self.assertEqual(len(a["changes"]),1)
            b=watch.tick();self.assertEqual(b["changes"][0]["state"],"critical")
            resumed=ChandradevFleetWatch(folder,{},transport=feed,clock=lambda:1001)
            c=resumed.tick();self.assertEqual(c["changes"],[])
            state=json.loads((Path(folder)/"fleet-health-history.json").read_text())
            self.assertEqual(len(state["events"]),2)
            self.assertEqual(state["last"]["suryadev-01"],"critical")
    def test_unknown_public_ip_and_short_credentials_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"token.txt").write_text("s"*64)
            cfg={"schema":SCHEMA,"endpoint":"https://10.0.0.5:8766",
                 "cert_sha256":"b"*64,"device_id":"chandradev-01",
                 "token_file":"token.txt"}
            (root/"watch.json").write_text(json.dumps(cfg))
            self.assertEqual(load_config(root/"watch.json")["host"],"10.0.0.5")
            cfg["endpoint"]="https://8.8.8.8"
            (root/"watch.json").write_text(json.dumps(cfg))
            with self.assertRaises(ValueError):
                load_config(root/"watch.json")

if __name__=="__main__":
    unittest.main()
