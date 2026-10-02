from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import ast,hashlib,json,re

@dataclass(frozen=True)
class CodeNode:
    id:str;kind:str;file:str;name:str;line:int
    def as_dict(self):return asdict(self)

class CodeBrain:
    """Deterministic, local structural index. Python AST is native; other languages use safe lexical extraction until a pinned Tree-sitter adapter is available."""
    TEXT_EXT={".py",".js",".jsx",".ts",".tsx",".dart",".java",".rs",".go"}
    IGNORE={".git","node_modules",".venv","venv","dist","build",".krishna_state"}
    def index(self,root):
        root=Path(root).resolve();nodes=[];edges=[];tests=set()
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in self.TEXT_EXT or any(x in self.IGNORE for x in p.relative_to(root).parts):continue
            rel=p.relative_to(root).as_posix()
            try:text=p.read_text(encoding="utf-8")
            except Exception:continue
            if "test" in p.name.lower() or "/tests/" in f"/{rel.lower()}/":tests.add(rel)
            if p.suffix==".py":
                try:tree=ast.parse(text,filename=rel)
                except SyntaxError:continue
                for n in ast.walk(tree):
                    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                        kind="class" if isinstance(n,ast.ClassDef) else "function";nid=f"{rel}:{kind}:{n.name}"
                        nodes.append(CodeNode(nid,kind,rel,n.name,getattr(n,"lineno",0)).as_dict())
                    if isinstance(n,(ast.Import,ast.ImportFrom)):
                        mod=(getattr(n,"module",None) or ",".join(x.name for x in n.names))
                        edges.append({"source":rel,"target":mod,"kind":"imports"})
            else:
                for m in re.finditer(r"(?m)^\s*(?:export\s+)?(?:async\s+)?(?:class|function|interface|enum|type)\s+([A-Za-z_$][\w$]*)",text):
                    name=m.group(1);nodes.append(CodeNode(f"{rel}:symbol:{name}","symbol",rel,name,text.count("\n",0,m.start())+1).as_dict())
                for m in re.finditer(r"""(?m)^\s*import\s+.*?from\s+['"]([^'"]+)['"]""",text):
                    edges.append({"source":rel,"target":m.group(1),"kind":"imports"})
        payload={"version":1,"root":str(root),"nodes":nodes,"edges":edges,"test_files":sorted(tests)}
        payload["digest"]=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        return payload
    def blast_radius(self,index,query):
        q=str(query or "").lower();seed={n["file"] for n in index.get("nodes",[]) if q in n["name"].lower() or q in n["file"].lower()}
        impacted=set(seed);changed=True
        while changed:
            changed=False
            for e in index.get("edges",[]):
                if any(x in str(e["target"]) for x in impacted) and e["source"] not in impacted:impacted.add(e["source"]);changed=True
        return {"query":query,"seed":sorted(seed),"impacted":sorted(impacted),"count":len(impacted)}
