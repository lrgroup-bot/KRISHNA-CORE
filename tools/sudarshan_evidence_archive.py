"""Content-addressed, project-scoped raw evidence artifacts.

Raw REA/MiroFish JSON is stored on the KRISHNA host, never in Git or logs.
The sha256 evidence identifier always commits to the exact stored JSON bytes.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

_ALLOWED_ENGINES = frozenset(("REA", "MiroFish", "UI_GUARDIAN"))
_ID = re.compile(r"^sha256:([0-9a-f]{64})$")
MAX_BYTES = 5_000_000


def _location(root, project, engine, evidence_id=None):
    if not isinstance(root, (str, Path)) or not Path(root).is_absolute():
        raise ValueError("absolute local evidence root required")
    if not isinstance(project, str) or not project.strip() or len(project) > 128:
        raise ValueError("bounded project identifier required")
    if engine not in _ALLOWED_ENGINES:
        raise ValueError("unsupported evidence engine")
    root = Path(root).resolve()
    project_key = hashlib.sha256(project.encode("utf-8")).hexdigest()
    area = root / project_key / engine
    if evidence_id is None:
        return area
    match = _ID.fullmatch(str(evidence_id))
    if not match:
        raise ValueError("sha256 evidence identifier required")
    return area / (match.group(1) + ".json")


def archive(root, project, engine, payload):
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_BYTES:
        raise ValueError("bounded JSON evidence bytes required")
    try:
        parsed = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("evidence must be valid UTF-8 JSON") from error
    if not isinstance(parsed, (dict, list)) or not parsed:
        raise ValueError("nonempty JSON object/array required")
    digest = hashlib.sha256(payload).hexdigest()
    evidence_id = "sha256:" + digest
    target = _location(root, project, engine, evidence_id)
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    # A temporary file in the same directory guarantees atomic rename.
    fd, name = tempfile.mkstemp(prefix=".pending-",suffix=".tmp",dir=parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            try:
                os.fchmod(stream.fileno(), 0o600)
            except (AttributeError, OSError):
                pass
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Never silently replace a same-digest file whose bytes differ.
        if target.exists():
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise RuntimeError("existing evidence artifact corrupted")
        else:
            os.replace(name, target)
            name = None
    finally:
        if name is not None:
            try:
                Path(name).unlink(missing_ok=True)
            except OSError:
                pass
    return evidence_id


def verify(root, project, engine, evidence_id):
    target = _location(root, project, engine, evidence_id)
    if not target.is_file():
        return False
    if target.is_symlink() or target.stat().st_size > MAX_BYTES:
        return False
    contents = target.read_bytes()
    return hashlib.sha256(contents).hexdigest() == evidence_id.removeprefix("sha256:")


def load(root, project, engine, evidence_id):
    if not verify(root, project, engine, evidence_id):
        raise ValueError("missing, cross-project, or corrupted evidence artifact")
    return json.loads(_location(root, project, engine, evidence_id).read_bytes())
