from __future__ import annotations

from pathlib import Path
from typing import Any
import json


class CandidateRepairGuard:
    """Minimal model-assisted repair confined to an isolated candidate workspace."""

    EXTENSIONS={".py",".html",".htm",".css",".scss",".js",".jsx",".ts",".tsx",".vue",".svelte",".java",".json"}
    EXCLUDES={".git",".venv","node_modules","dist","build",".krishna_state",".github","coverage",".next",".nuxt"}
    SENSITIVE={".env",".env.local",".npmrc","credentials.json","secrets.json","id_rsa","id_ed25519",
               "package-lock.json","pnpm-lock.yaml","yarn.lock","requirements.txt","pyproject.toml","package.json"}
    MAX_FILES=12
    MAX_FILE_CHARS=50000
    MAX_TOTAL_CONTEXT=150000

    @classmethod
    def collect_context(cls, candidate_root: str | Path, hints: list[str] | None=None) -> dict[str,Any]:
        root=Path(candidate_root).resolve()
        if not root.is_dir():raise ValueError("candidate root does not exist")
        terms={str(x).lower() for x in (hints or []) if str(x).strip()}
        rows=[]
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in cls.EXTENSIONS:continue
            if path.name.lower() in cls.SENSITIVE or any(part in cls.EXCLUDES for part in path.parts):continue
            try:
                rel=str(path.relative_to(root)).replace("\\","/")
                text=path.read_text(encoding="utf-8")
            except Exception:continue
            hay=(rel+" "+text[:8000]).lower()
            score=sum(4 for term in terms if term and term in hay)
            if any(x in rel.lower() for x in ("src/","core/","app/","test","index.","main.","server","route","component")):score+=2
            rows.append((score,rel,text[:cls.MAX_FILE_CHARS]))
        rows.sort(key=lambda x:(-x[0],len(x[1]),x[1]))
        out=[];used=0
        for score,rel,text in rows:
            if len(out)>=24 or used>=cls.MAX_TOTAL_CONTEXT:break
            snippet=text[:cls.MAX_TOTAL_CONTEXT-used]
            if not snippet:continue
            out.append({"path":rel,"content":snippet,"score":score});used+=len(snippet)
        return {"root":str(root),"files":out,"chars":used}

    @classmethod
    def validate_patch(cls, candidate_root: str | Path, files: list[dict[str,Any]]) -> list[dict[str,str]]:
        root=Path(candidate_root).resolve()
        if not files or not isinstance(files,list):raise ValueError("repair returned no files")
        if len(files)>cls.MAX_FILES:raise ValueError("repair returned too many files")
        out=[];total=0;seen=set()
        for row in files:
            if not isinstance(row,dict):raise ValueError("repair patch entries must be objects")
            rel=str(row.get("path") or "").replace("\\","/").strip("/")
            if not rel or rel.startswith("../") or "/../" in rel:raise ValueError("unsafe repair path")
            if rel in seen:raise ValueError("duplicate repair path")
            seen.add(rel)
            target=(root/rel).resolve()
            try:target.relative_to(root)
            except ValueError as exc:raise ValueError("repair escapes candidate") from exc
            if not target.is_file():raise PermissionError("auto-repair may modify existing candidate files only")
            if target.suffix.lower() not in cls.EXTENSIONS:raise PermissionError("auto-repair file type is not allowed")
            if target.name.lower() in cls.SENSITIVE or any(part in cls.EXCLUDES for part in target.parts):
                raise PermissionError("auto-repair cannot modify dependency, secret, workflow or build state")
            content=str(row.get("content") or "")
            if not content:raise ValueError("repair content is empty")
            if len(content)>cls.MAX_FILE_CHARS:raise ValueError("repair file exceeds size limit")
            total+=len(content)
            if total>cls.MAX_FILES*cls.MAX_FILE_CHARS:raise ValueError("repair exceeds total patch budget")
            out.append({"path":rel,"content":content})
        return out

    @staticmethod
    def apply(candidate_root: str | Path, files: list[dict[str,str]]) -> list[str]:
        root=Path(candidate_root).resolve();changed=[]
        for row in files:
            target=(root/row["path"]).resolve();target.relative_to(root)
            target.write_text(row["content"],encoding="utf-8");changed.append(row["path"])
        return changed

    @classmethod
    def prompt(cls, failures: list[dict[str,Any]], context: dict[str,Any]) -> str:
        failure_json=json.dumps(failures,ensure_ascii=False,default=str)[:40000]
        files="\n\n".join(f"--- FILE {x['path']} ---\n{x['content']}" for x in context.get("files") or [])
        return (
            "You are KRISHNA's isolated candidate repair worker. Fix only objective code defects represented by the supplied "
            "failed verification evidence. Do not bypass tests, delete assertions, weaken security/accessibility, suppress errors, "
            "change credentials, dependency manifests, CI workflows or external services. Make the smallest source fix that addresses "
            "root cause. Preserve existing functionality and API contracts.\n\n"
            f"FAILED GATES / EVIDENCE:\n{failure_json}\n\n"
            f"CANDIDATE SOURCE CONTEXT:\n{files}\n\n"
            "Return STRICT JSON only: "
            '{"summary":"root cause and repair","files":[{"path":"existing/relative/file","content":"COMPLETE replacement file"}]}. '
            f"At most {cls.MAX_FILES} files. No markdown fences."
        )
