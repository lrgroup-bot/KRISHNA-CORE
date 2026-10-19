import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from krishna_core.network_inventory import NetworkInventory, normalize_snapshot


class NetworkInventoryTests(unittest.TestCase):
    def fixture(self):
        return {"interfaces": [{"InterfaceIndex": 7, "IPAddress": "192.168.8.20", "PrefixLength": 24}],
                "routes": [{"InterfaceIndex": 7, "NextHop": "192.168.8.1", "RouteMetric": 20}],
                "neighbors": [{"InterfaceIndex": 7, "IPAddress": "192.168.8.1", "State": "Stale",
                               "LinkLayerAddress": "private-hardware-identity"}]}

    def test_passive_observation_never_claims_verified_connectivity_or_hardware_identity(self):
        runner = Mock(return_value=SimpleNamespace(stdout=json.dumps(self.fixture())))
        result = NetworkInventory(runner=runner, platform="nt").status()
        self.assertTrue(result["available"])
        self.assertFalse(result["scan_performed"])
        self.assertFalse(result["devices_verified"])
        self.assertEqual(result["devices"][0]["status"], "observed")
        self.assertEqual(result["devices"][0]["state"], "Stale")
        self.assertEqual(result["devices"][0]["kind"], "gateway")
        self.assertEqual(result["devices"][0]["recognition_source"], "OS default route")
        self.assertFalse(result["devices"][0]["identity_verified"])
        self.assertFalse(result["devices"][0]["connectivity_verified"])
        self.assertEqual(result["subnet"], "192.168.8.0/24")
        self.assertNotIn("private-hardware-identity", json.dumps(result))
        self.assertEqual(runner.call_args.kwargs["timeout"], 5)

    def test_cache_prevents_repeated_os_commands_and_callers_cannot_mutate_it(self):
        runner = Mock(return_value=SimpleNamespace(stdout=json.dumps(self.fixture())))
        clock = Mock(return_value=100)
        inventory = NetworkInventory(runner=runner, platform="nt", clock=clock)
        inventory.status()["devices"].clear()
        self.assertEqual(len(inventory.status()["devices"]), 1)
        self.assertEqual(runner.call_count, 1)
        clock.return_value = 131
        inventory.status()
        self.assertEqual(runner.call_count, 2)

    def test_timeouts_and_malformed_output_are_unavailable_without_private_errors(self):
        for failure in (subprocess.TimeoutExpired("private-command", 5),
                        OSError("private-user-location"), "not json", "[]"):
            runner = Mock(side_effect=failure) if isinstance(failure, Exception) else Mock(return_value=SimpleNamespace(stdout=failure))
            result = NetworkInventory(runner=runner, platform="nt").status()
            self.assertFalse(result["available"])
            self.assertEqual(result["devices"], [])
            self.assertNotIn("private-", json.dumps(result))

    def test_platform_without_windows_is_honestly_unavailable(self):
        runner = Mock()
        self.assertFalse(NetworkInventory(runner=runner, platform="posix").status()["available"])
        runner.assert_not_called()

    def test_change_watch_baselines_cache_and_recovers_without_false_disconnects(self):
        raw = self.fixture()
        runner = Mock(return_value=SimpleNamespace(stdout=json.dumps(raw)))
        clock = Mock(return_value=100)
        inventory = NetworkInventory(runner=runner, platform="nt", clock=clock)
        self.assertEqual(inventory.status()["changes"], [])
        raw["neighbors"].append({"InterfaceIndex": 7, "IPAddress": "192.168.8.2", "State": "Reachable"})
        runner.return_value.stdout = json.dumps(raw)
        clock.return_value = 131
        result = inventory.status()
        self.assertEqual([(row["kind"], row["ip"]) for row in result["changes"]], [("newly_observed", "192.168.8.2")])
        result["changes"].clear()
        self.assertEqual(len(inventory.status()["changes"]), 1)
        clock.return_value = 162
        runner.side_effect = OSError("private failure")
        self.assertFalse(inventory.status()["available"])
        clock.return_value = 193
        runner.side_effect = None
        self.assertEqual(len(inventory.status()["changes"]), 1)
        clock.return_value = 224
        raw["neighbors"].pop()
        runner.return_value.stdout = json.dumps(raw)
        changes = inventory.status()["changes"]
        self.assertEqual(changes[-1]["kind"], "no_longer_observed")
        self.assertFalse(changes[-1]["identity_verified"])

    def test_change_history_is_bounded_and_successive_new_entries_are_not_repeated(self):
        runner = Mock()
        clock = Mock(return_value=0)
        inventory = NetworkInventory(runner=runner, platform="nt", clock=clock, cache_seconds=1)
        for index in range(72):
            raw = self.fixture()
            raw["neighbors"] = [{"InterfaceIndex": 7, "IPAddress": f"192.168.8.{index + 100}", "State": "Stale"}]
            runner.return_value = SimpleNamespace(stdout=json.dumps(raw))
            clock.return_value = index * 2
            result = inventory.status()
        self.assertEqual(len(result["changes"]), 64)
        self.assertEqual(result["change_sequence"], 142)
        clock.return_value += 2
        self.assertEqual(inventory.status()["change_sequence"], 142)

    def test_invalid_unresolved_and_non_device_addresses_are_ignored(self):
        raw = self.fixture()
        raw["neighbors"] += [raw["neighbors"][0], {"InterfaceIndex": 7, "IPAddress": "192.168.8.2", "State": "Incomplete"}]
        for address in ("invalid", "127.0.0.1", "0.0.0.0", "224.0.0.1", "255.255.255.255", "169.254.0.1"):
            raw["neighbors"].append({"InterfaceIndex": 7, "IPAddress": address, "State": "Reachable"})
        self.assertEqual(len(normalize_snapshot(raw)["devices"]), 1)

    def test_single_object_output_and_ipv6_prefixes_are_supported(self):
        result = normalize_snapshot({"interfaces": {"InterfaceIndex": 4, "IPAddress": "fd00::20", "PrefixLength": 64},
                                     "routes": {"InterfaceIndex": 4, "NextHop": "fd00::1", "RouteMetric": 10},
                                     "neighbors": None})
        self.assertEqual(result["subnet"], "fd00::/64")
        self.assertEqual(result["gateway"], "fd00::1")

    def test_subnet_broadcast_network_and_own_addresses_are_not_devices(self):
        raw = self.fixture()
        for address in ('192.168.8.255', '192.168.8.0', '192.168.8.20'):
            raw['neighbors'].append({'InterfaceIndex': 7, 'IPAddress': address, 'State': 'Permanent'})
        raw['interfaces'].append({'InterfaceIndex': 8, 'IPAddress': 'fe80::1234%8', 'PrefixLength': 64})
        raw['neighbors'].append({'InterfaceIndex': 8, 'IPAddress': 'fe80::1234', 'State': 'Stale'})
        self.assertEqual([row['ip'] for row in normalize_snapshot(raw)['devices']], ['192.168.8.1'])
