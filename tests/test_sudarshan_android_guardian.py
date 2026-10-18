import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.sudarshan_android_guardian import inventory_android

XML = '<?xml version="1.0" encoding="UTF-8"?><hierarchy>' + (
    '<node text="Launch" clickable="true" resource-id="com.lr.krishna:id/launch" '
    'bounds="[0,0][100,50]" content-desc="Launch">'
    '<node text="Current view" clickable="false"/></node></hierarchy>')


class AndroidInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.adb=Path(self.tmp.name)/"adb"
        self.adb.write_text("fixture")
        self.seen=[]
    def fake(self, command, **kwargs):
        self.seen.append(command)
        self.assertFalse(kwargs['shell'])
        self.assertEqual(command[1:3],['-s','android-primary'])
        args=command[3:]
        result={
            ("get-state",):"device\n",
            ("shell","pm","path","com.lr.krishna"):"package:/data/app/com.lr.krishna/base.apk\n",
            ("shell","dumpsys","window"):"mCurrentFocus=Window{22 com.lr.krishna/.MainActivity}\n",
            ("exec-out","uiautomator","dump","/dev/tty"):XML,
        }.get(tuple(args))
        return SimpleNamespace(returncode=0 if result is not None else 1,
                               stdout=result or "",stderr="")
    def inspect(self,**kwargs):
        return inventory_android(adb_executable=self.adb.resolve(),
                device_serial='android-primary',app_package='com.lr.krishna',
                authorized=True,runner=self.fake,**kwargs)
    def test_real_subprocess_contract_without_tapping(self):
        result=self.inspect()
        self.assertEqual(result.status,'passed')
        self.assertIn('2 nodes, 1 clickable',result.summary)
        self.assertTrue(result.evidence_id.startswith('sha256:'))
        self.assertEqual(len(self.seen),4)
        self.assertFalse(any('input' in c or 'install' in c for cmd in self.seen for c in cmd))
    def test_raw_mobile_evidence_locally_archived(self):
        from tools.sudarshan_evidence_archive import verify, load
        root=(Path(self.tmp.name)/'evidence').resolve()
        result=self.inspect(evidence_root=root,project_id='k')
        self.assertTrue(verify(root,'k','UI_GUARDIAN',result.evidence_id))
        data=load(root,'k','UI_GUARDIAN',result.evidence_id)
        self.assertEqual(data['nodes'],2)
        self.assertEqual(data['interactions_performed'],0)
    def test_unapproved_device_and_package_blocked(self):
        with self.assertRaises(PermissionError):
            inventory_android(adb_executable=self.adb.resolve(),
                              device_serial='android-primary',app_package='com.lr.krishna')
        with self.assertRaises(ValueError):
            inventory_android(adb_executable=self.adb.resolve(),
                              device_serial='x; rm -rf /',app_package='com.lr.krishna',
                              authorized=True)
        with self.assertRaises(ValueError):
            inventory_android(adb_executable=self.adb.resolve(),
                              device_serial='android-primary',app_package='../../etc/passwd',
                              authorized=True)
    def test_foreground_mismatch_cannot_count_as_pass(self):
        def wrong_focus(command,**kwargs):
            if command[3:]==['shell','dumpsys','window']:
                return SimpleNamespace(returncode=0,stdout='mCurrentFocus=com.other.app/.Main')
            return self.fake(command,**kwargs)
        result=inventory_android(adb_executable=self.adb.resolve(),
            device_serial='android-primary',app_package='com.lr.krishna',
            authorized=True,runner=wrong_focus)
        self.assertEqual(result.status,'not_tested')
        self.assertFalse(result.evidence_id)

if __name__=='__main__':
    unittest.main()
