"""Sudarshan advisory duplicate detector: Python AST structural signatures.

No network, code execution, or destructive edits. Similarity is a review hint,
not proof that functions are redundant.
"""
from __future__ import annotations
import ast
from collections import defaultdict
from pathlib import Path

SKIP={".git",".venv","venv","node_modules","__pycache__","build","dist"}

def _shape(node):
    """Normalize identifiers while preserving control flow and operations."""
    class Normalize(ast.NodeTransformer):
        def visit_Name(self,n):
            return ast.copy_location(ast.Name(id="_",ctx=n.ctx),n)
        def visit_arg(self,n):
            return ast.copy_location(ast.arg(arg="_",annotation=None,type_comment=None),n)
        def visit_Constant(self,n):
            return ast.copy_location(ast.Constant(value=type(n.value).__name__),n)
    body=ast.Module(body=node.body, type_ignores=[])
    return ast.dump(Normalize().visit(body),include_attributes=False)

def duplicate_candidates(root, *, max_files=3000, max_pairs=150):
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise ValueError("root must be directory")
    groups=defaultdict(list)
    count=0
    for path in root.rglob("*.py"):
        if any(x in SKIP for x in path.relative_to(root).parts):continue
        count+=1
        if count>max_files:break
        try:
            source=path.read_text(encoding="utf-8")
            if len(source)>500_000:continue
            tree=ast.parse(source)
        except (OSError,UnicodeError,SyntaxError):continue
        for node in ast.walk(tree):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
            if len(node.body)<3:continue
            signature=_shape(node)
            groups[signature].append({"file":str(path.relative_to(root)),
                                      "symbol":node.name,"line":node.lineno})
    pairs=[]
    for group in groups.values():
        if len(group)<2:continue
        for i in range(len(group)):
            for j in range(i+1,len(group)):
                if group[i]["file"]==group[j]["file"]:continue
                pairs.append({"left":group[i],"right":group[j],
                              "status":"review_only","reason":"matching normalized Python AST"})
                if len(pairs)>=max_pairs:
                    return {"files_scanned":count,"candidates":pairs,"truncated":True}
    return {"files_scanned":count,"candidates":pairs,"truncated":count>max_files}
