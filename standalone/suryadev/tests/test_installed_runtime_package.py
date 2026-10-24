"""Regression for omitted installed modules (e.g. suryadev_fleet_client)."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from verify_runtime_package import missing_runtime_files, REQUIRED_FRONTEND


SOURCE = Path(__file__).resolve().parents[1]
REPO = SOURCE.parents[1]
INSTALLER = SOURCE / "install-windows.ps1"
WORKER = REPO / "core" / "suryadev_worker.py"
ADAPTER = REPO / "scripts" / "SURYDEV_VIDEO_LEARNING_ADAPTER.py"


def packaged_files():
    installer = INSTALLER.read_text(encoding="utf-8")
    match = re.search(r"\$files\s*=\s*@\((.*?)\)\s*foreach\s*\(\$name\s+in\s+\$files\)",
                      installer, re.S)
    if not match:
        raise AssertionError("Could not parse the installer package manifest")
    return set(re.findall(r"'([^']+)'", match.group(1)))


class InstallerPackageContract(unittest.TestCase):
    def test_all_python_modules_are_packaged(self):
        files = packaged_files()
        missing = {p.name for p in SOURCE.glob("*.py")} - files
        self.assertEqual(missing, set(), f"Source modules omitted from Windows installer: {missing}")
        self.assertIn("suryadev_fleet_client.py", files)
        self.assertIn("verify_runtime_package.py", files)

    def test_original_repo_frontend_assets_are_packaged(self):
        files = packaged_files()
        missing = set(REQUIRED_FRONTEND) - files
        self.assertEqual(missing, set())
        self.assertFalse(any(x.lower().startswith("r39-web") for x in files))
        self.assertIn("-I (Join-Path $destination 'verify_runtime_package.py')", INSTALLER.read_text(encoding="utf-8"))

    def test_installed_clean_room_imports_and_missing_dependency_fail(self):
        if not (WORKER.is_file() and ADAPTER.is_file()):
            self.fail("Cannot stage installed package: canonical worker or adapter absent")
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for name in packaged_files():
                shutil.copy2(SOURCE / name, target / name)
            shutil.copy2(WORKER, target / "suryadev_r39_worker.py")
            shutil.copy2(ADAPTER, target / "suryadev_r39_adapter.py")
            cmd = [sys.executable, "-I", str(target / "verify_runtime_package.py"),
                   "--root", str(target)]
            complete = subprocess.run(cmd, text=True, capture_output=True,
                                      cwd=temp, timeout=45)
            self.assertEqual(complete.returncode, 0, complete.stderr + complete.stdout)
            # Deliberately reproduce user's real-world failure.
            (target / "suryadev_fleet_client.py").unlink()
            missing = subprocess.run(cmd, text=True, capture_output=True,
                                     cwd=temp, timeout=45)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("suryadev_fleet_client", missing.stderr)

    def test_missing_dependencies_found_without_running_app(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "suryadev_extras.py").write_text(
                "def start():\n    from suryadev_fleet_client import FleetClient\n",
                encoding="utf-8")
            errors = missing_runtime_files(root)
            self.assertTrue(any("suryadev_fleet_client.py" in x for x in errors))


if __name__ == "__main__":
    unittest.main()
