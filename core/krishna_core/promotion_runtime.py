from __future__ import annotations
from pathlib import Path
import shutil,tempfile


class PromotionRuntime:
    """Compatibility promotion helper with scoped paths, backup and rollback.

    New project promotion should prefer PromotionManager. This class remains for
    compatibility but is fail-closed against path traversal and out-of-root files.
    """

    @staticmethod
    def _safe(root,relative):
        root=Path(root).resolve()
        rel=str(relative or "").replace("\\","/").strip("/")
        if not rel or rel.startswith("../") or "/../" in ("/"+rel):
            raise ValueError("invalid relative promotion path")
        target=(root/rel).resolve()
        try:target.relative_to(root)
        except ValueError as exc:raise ValueError("promotion path escapes root") from exc
        return rel,target

    def promote(self,shadow,working,relative_files,verified):
        if not verified:raise PermissionError("verification required before promotion")
        shadow,working=Path(shadow).resolve(),Path(working).resolve()
        if not shadow.is_dir() or not working.is_dir():
            raise ValueError("shadow and working roots must be directories")
        backup=Path(tempfile.mkdtemp(prefix="krishna-backup-"))
        changed=[]
        try:
            for raw in relative_files:
                rel,src=self._safe(shadow,raw)
                _,dst=self._safe(working,rel)
                if not src.is_file():raise FileNotFoundError(str(src))
                if dst.exists():
                    if not dst.is_file():raise ValueError("promotion target is not a file")
                    b=backup/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,b)
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);changed.append(rel)
            return {"promoted":True,"files":changed,"backup":str(backup)}
        except Exception:
            for rel in changed:
                _,dst=self._safe(working,rel)
                b=(backup/rel).resolve()
                if b.is_file():shutil.copy2(b,dst)
                elif dst.exists() and dst.is_file():dst.unlink()
            raise

    def rollback(self,working,backup,relative_files):
        working,backup=Path(working).resolve(),Path(backup).resolve()
        restored=[]
        for raw in relative_files:
            rel,dst=self._safe(working,raw)
            b=(backup/rel).resolve()
            try:b.relative_to(backup)
            except ValueError as exc:raise ValueError("backup path escapes root") from exc
            if b.is_file():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(b,dst)
            elif dst.exists() and dst.is_file():dst.unlink()
            restored.append(rel)
        return {"rolled_back":True,"files":restored}
