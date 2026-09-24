import base64
import hashlib
import tempfile
import unittest
from pathlib import Path

from krishna_core.hawkeye_media_sync import HawkeyeMediaSyncStore


class HawkeyeMediaSyncTests(unittest.TestCase):
    def test_resumable_chunk_upload_sha256_and_atomic_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            store=HawkeyeMediaSyncStore(Path(td))
            payload=(b"krishna-hawkeye-"*50000)[:700000]
            digest=hashlib.sha256(payload).hexdigest()
            start=store.start(
                observation_id="obs-1",session_id="field-1",filename="capture.mp4",
                size_bytes=len(payload),sha256=digest,content_type="video/mp4",
                modality="video",metadata={"source":"mobile"},
            )
            self.assertEqual(start["next_offset"],0)
            first=payload[:400000]
            row=store.append(start["upload_id"],0,base64.b64encode(first).decode())
            self.assertEqual(row["next_offset"],len(first))

            resumed=store.start(
                observation_id="obs-1",session_id="field-1",filename="capture.mp4",
                size_bytes=len(payload),sha256=digest,content_type="video/mp4",
                modality="video",metadata={"source":"mobile"},
            )
            self.assertEqual(resumed["next_offset"],len(first))

            rest=payload[len(first):]
            row=store.append(start["upload_id"],len(first),base64.b64encode(rest).decode())
            self.assertEqual(row["status"],"VERIFYING")
            done=store.complete(start["upload_id"])
            self.assertTrue(done["verified"])
            self.assertTrue(done["retained_pc"])
            final=Path(done["path"])
            self.assertTrue(final.is_file())
            self.assertEqual(final.read_bytes(),payload)
            self.assertFalse(store._part_path(start["upload_id"]).exists())

    def test_resume_required_and_hash_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            store=HawkeyeMediaSyncStore(Path(td))
            payload=b"abc123"
            digest=hashlib.sha256(b"different").hexdigest()
            start=store.start(
                observation_id="obs-2",session_id="field",filename="x.bin",
                size_bytes=len(payload),sha256=digest,
            )
            mismatch=store.append(start["upload_id"],3,base64.b64encode(payload).decode())
            self.assertEqual(mismatch["status"],"RESUME_REQUIRED")
            store.append(start["upload_id"],0,base64.b64encode(payload).decode())
            with self.assertRaises(ValueError):
                store.complete(start["upload_id"])
            self.assertEqual(store.status(start["upload_id"])["status"],"FAILED")


if __name__=="__main__":
    unittest.main()
