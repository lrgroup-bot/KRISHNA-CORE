"""Plugin signatures must be verified before being listed as trusted.

The registry MUST NOT execute third-party code. Optional cryptography is
needed only for the positive Ed25519 signature acceptance case.
"""
import base64
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from suryadev_plugins import plugin_registry, verify_manifest


class PluginRegistryTests(unittest.TestCase):
    def test_empty_registry_never_executes_code(self):
        with TemporaryDirectory() as t:
            r=plugin_registry(t)
            self.assertEqual(r["plugins"],[])
            self.assertFalse(r["execution_enabled"])

    def test_untrusted_plugin_fails_closed_without_importing(self):
        with TemporaryDirectory() as t:
            root=Path(t)
            mod=root/"plugins"/"sample"
            mod.mkdir(parents=True)
            payload=b'raise RuntimeError("DO NOT EXECUTE")\n'
            (mod/"plugin.py").write_bytes(payload)
            record={"schema":"suryadev.plugin.v1","plugin_id":"sample","api_version":1,
                    "kind":"pdf","entrypoint":"plugin.py",
                    "sha256":hashlib.sha256(payload).hexdigest(),
                    "key_id":"approved","signature":base64.b64encode(b"0"*64).decode()}
            (mod/"manifest.json").write_text(json.dumps(record))
            outcome=plugin_registry(root)
            self.assertEqual(len(outcome["rejected"]),1)
            self.assertEqual(outcome["plugins"],[])
            self.assertFalse(outcome["execution_enabled"])
            record["entrypoint"]="../escape.py"
            (mod/"manifest.json").write_text(json.dumps(record))
            self.assertEqual(plugin_registry(root)["plugins"],[])

    def test_valid_ed25519_signed_plugin_still_never_runs(self):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            self.skipTest("Optional cryptography dependency is not installed")
        with TemporaryDirectory() as t:
            root=Path(t)
            folder=root/"plugins"/"secure"
            folder.mkdir(parents=True)
            payload=b'raise RuntimeError("must not execute")\n'
            (folder/"worker.py").write_bytes(payload)
            key=Ed25519PrivateKey.generate()
            pub=key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw)
            trust=root/"plugin-trust"/"keys"
            trust.mkdir(parents=True)
            (trust/"owner.pub").write_text(pub.hex())
            manifest={"schema":"suryadev.plugin.v1","plugin_id":"secure","api_version":1,
                      "kind":"book","entrypoint":"worker.py",
                      "sha256":hashlib.sha256(payload).hexdigest(),"key_id":"owner"}
            canonical=json.dumps(manifest,sort_keys=True,separators=(",",":"),
                                 ensure_ascii=False).encode("utf-8")
            manifest["signature"]=base64.b64encode(key.sign(canonical)).decode()
            (folder/"manifest.json").write_text(json.dumps(manifest))
            report=plugin_registry(root)
            self.assertEqual(len(report["plugins"]),1)
            self.assertFalse(report["plugins"][0]["execution_enabled"])
            self.assertEqual(report["rejected"],[])
            (folder/"worker.py").write_bytes(b'changed\n')
            self.assertEqual(plugin_registry(root)["plugins"],[])
            self.assertEqual(len(plugin_registry(root)["rejected"]),1)


if __name__=="__main__":
    unittest.main()
