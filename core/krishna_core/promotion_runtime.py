from __future__ import annotations
from pathlib import Path
import shutil,tempfile


class PromotionRuntime:
    """Promote verified shadow files with backup + rollback."""

    @staticmethod
    def _safe_target(root:Path,rel)->Path:
        raw=str(rel or "").replace("\\","/").strip("/")
        if not raw or raw.startswith("../") or "/../" in raw or raw=="..":
            raise ValueError("invalid relative promotion path")
        root=root.resolve()
        target=(root/raw).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("promotion path escapes root") from exc
        return target

    def promote(self,shadow,working,relative_files,verified):
        if not verified:raise PermissionError("verification required before promotion")
        shadow,working=Path(shadow).resolve(),Path(working).resolve()
        if not shadow.is_dir() or not working.is_dir():
            raise ValueError("shadow and working roots must be directories")
        files=[str(x) for x in relative_files]
        backup=Path(tempfile.mkdtemp(prefix="krishna-backup-"))
        changed=[]
        try:
            for rel in files:
                src=self._safe_target(shadow,rel);dst=self._safe_target(working,rel)
                if not src.is_file():raise FileNotFoundError(str(src))
                if dst.exists():
                    b=self._safe_target(backup,rel);b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,b)
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);changed.append(rel)
            return {"promoted":True,"files":changed,"backup":str(backup)}
        except Exception:
            for rel in changed:
                b=self._safe_target(backup,rel);dst=self._safe_target(working,rel)
                if b.exists():shutil.copy2(b,dst)
                elif dst.exists():dst.unlink()
            raise

    def rollback(self,working,backup,relative_files):
        working,backup=Path(working).resolve(),Path(backup).resolve()
        for rel in [str(x) for x in relative_files]:
            b=self._safe_target(backup,rel);dst=self._safe_target(working,rel)
            if b.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(b,dst)
            elif dst.exists():dst.unlink()
        return {"rolled_back":True,"files":list(relative_files)}
