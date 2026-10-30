"""Windows WinError 5/32 resilience without losing atomic telemetry semantics.

Synthetic WinError cases run on both Linux and Windows CI. Persistent errors
still propagate; no in-place JSON truncation, chmod, lock removal or reset.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from suryadev_liveops import atomic_json, _WINDOWS_REPLACE_DELAYS


def windows_denied(winerror=5):
    error = PermissionError(13, "Access is denied")
    error.winerror = winerror
    return error


class AtomicRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.target = self.root / "worker-runtime.json"
        self.target.write_text('{"state":"old"}', encoding="utf-8")

    def test_winerror5_retries_then_atomically_commits_valid_json(self):
        original = os.replace
        calls = []

        def share_locked(source, destination):
            calls.append((source, destination))
            if len(calls) < 3:
                raise windows_denied(5)
            return original(source, destination)

        with patch("suryadev_liveops.os.replace", side_effect=share_locked), \
             patch("suryadev_liveops.time.sleep") as sleeping:
            atomic_json(self.root, "worker-runtime.json", {"state":"busy","heartbeat_at":7})
        self.assertEqual(json.loads(self.target.read_text()), {
            "state":"busy", "heartbeat_at":7})
        self.assertEqual(len(calls),3)
        self.assertEqual(sleeping.call_count,2)
        self.assertFalse(list(self.root.glob("*.tmp")))

    def test_winerror32_and33_get_bounded_retry(self):
        for error_code in (32, 33):
            def one_lock(source, destination):
                if not hasattr(one_lock,"seen"):
                    one_lock.seen=True
                    raise windows_denied(error_code)
                return os_replace(source,destination)
            os_replace=os.replace
            with patch("suryadev_liveops.os.replace", side_effect=one_lock), \
                 patch("suryadev_liveops.time.sleep") as sleeping:
                atomic_json(self.root, "worker-runtime.json", {"winerror":error_code})
            self.assertEqual(sleeping.call_count,1)
            self.assertEqual(json.loads(self.target.read_text()),{"winerror":error_code})

    def test_persistent_winerror_never_truncates_previous_receipt(self):
        original=self.target.read_bytes()
        with patch("suryadev_liveops.os.replace", side_effect=windows_denied(5)) as replacing, \
             patch("suryadev_liveops.time.sleep") as sleeping:
            with self.assertRaises(PermissionError):
                atomic_json(self.root,"worker-runtime.json",{"state":"new"})
        self.assertEqual(replacing.call_count,len(_WINDOWS_REPLACE_DELAYS)+1)
        self.assertEqual(sleeping.call_count,len(_WINDOWS_REPLACE_DELAYS))
        self.assertEqual(self.target.read_bytes(),original)
        self.assertFalse(list(self.root.glob("*.tmp")))

    def test_unrelated_permission_errors_are_not_retried(self):
        original=self.target.read_bytes()
        with patch("suryadev_liveops.os.replace",side_effect=windows_denied(123)), \
             patch("suryadev_liveops.time.sleep") as sleeping:
            with self.assertRaises(PermissionError):
                atomic_json(self.root,"worker-runtime.json",{"state":"new"})
        sleeping.assert_not_called()
        self.assertEqual(self.target.read_bytes(),original)

    def test_unrelated_io_errors_fail_closed(self):
        original=self.target.read_bytes()
        with patch("suryadev_liveops.os.replace",side_effect=FileNotFoundError("disk unavailable")), \
             patch("suryadev_liveops.time.sleep") as sleeping:
            with self.assertRaises(FileNotFoundError):
                atomic_json(self.root,"worker-runtime.json",{"state":"new"})
        sleeping.assert_not_called()
        self.assertEqual(self.target.read_bytes(),original)


if __name__ == "__main__":
    unittest.main()
