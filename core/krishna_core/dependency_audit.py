"""Local dependency/SBOM inventory for KABACH.

Inventory only: it never installs, upgrades or executes packages. Vulnerability
matching is supplied by vetted advisory data at a higher layer.
"""
from __future__ import annotations
from pathlib import Path
import json,re

class DependencyAuditor:
    def inventory(self,root):
        root=Path(root); packages=[]
        req=root/"requirements.txt"
        if req.exists():
            for line in req.read_text(encoding="utf-8",errors="ignore").splitlines():
                line=line.strip()
                if not line or line.startswith(("#","-")): continue
                m=re.match(r"([A-Za-z0-9_.-]+)\s*(?:==|>=|<=|~=|!=|>|<)?\s*([^;\s]+)?",line)
                if m: packages.append({"ecosystem":"pypi","name":m.group(1),"version":m.group(2) or None,"source":"requirements.txt"})
        pkg=root/"package.json"
        if pkg.exists():
            try:
                data=json.loads(pkg.read_text(encoding="utf-8"))
                for section in ("dependencies","devDependencies"):
                    for name,version in (data.get(section) or {}).items():
                        packages.append({"ecosystem":"npm","name":name,"version":str(version),"source":"package.json"})
            except (OSError,json.JSONDecodeError): pass
        return {"root":str(root.resolve()),"packages":packages,"count":len(packages),
                "mutated":False,"advisory_matching":"separate_vetted_step"}

    def sbom(self,root):
        inv=self.inventory(root)
        return {"bomFormat":"CycloneDX","specVersion":"1.5","version":1,
                "components":[{"type":"library","name":x["name"],"version":x["version"],
                               "purl":f"pkg:{x['ecosystem']}/{x['name']}"} for x in inv["packages"]]}
