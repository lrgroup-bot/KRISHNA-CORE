"""Read-only, stdlib-only Sudarshan scope and complexity review.

Inspired by the MIT-licensed Ponytail methodology; original implementation.
This is an advisory preflight, never an authorization or a test substitute.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path


class SudarshanLeanReview:
    MODES = ('lite', 'full', 'ultra')
    EXTENSIONS = {'.py', '.js', '.mjs', '.ts', '.tsx', '.java', '.ps1'}
    SKIP = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build'}

    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError('root must be a directory')

    def _path(self, name):
        if not isinstance(name, str) or not name.strip():
            raise ValueError('file path required')
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            raise ValueError('path outside repository or not a file')
        if any(part in self.SKIP for part in path.relative_to(self.root).parts):
            raise ValueError('excluded path')
        return path

    def _files(self, max_files=3000):
        count = 0
        for path in self.root.rglob('*'):
            if any(part in self.SKIP for part in path.relative_to(self.root).parts):
                continue
            if path.is_file() and path.suffix in self.EXTENSIONS:
                count += 1
                if count > max_files:
                    return
                yield path

    @staticmethod
    def _symbols(source, extension):
        if extension == '.py':
            try:
                tree = ast.parse(source)
            except SyntaxError:
                return set()
            return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        return set(re.findall(r'\b(?:function|class)\s+([A-Za-z_$][\w$]*)', source))

    def review(self, changed_files, *, mode='full', proposed_dependencies=(), max_files=3000):
        if mode not in self.MODES:
            raise ValueError('unknown review mode')
        if not isinstance(changed_files, (list, tuple)) or not changed_files or len(changed_files) > 100:
            raise ValueError('changed_files must contain 1-100 paths')
        changed = {self._path(name) for name in changed_files}
        sources = {}
        for path in self._files(max_files=max_files):
            try:
                sources[path] = path.read_text(encoding='utf-8')[:500_000]
            except (UnicodeError, OSError):
                continue
        findings = []
        for path in sorted(changed):
            if path not in sources:
                findings.append({'kind': 'unscanned', 'file': str(path.relative_to(self.root)), 'severity': 'warning'})
                continue
            rel = str(path.relative_to(self.root))
            symbols = self._symbols(sources[path], path.suffix)
            for symbol in sorted(symbols):
                if len(symbol) < 4 or symbol.startswith('_'):
                    continue
                matches = [str(p.relative_to(self.root)) for p, body in sources.items()
                           if p != path and re.search(r'\b' + re.escape(symbol) + r'\b', body)]
                if matches:
                    findings.append({'kind': 'existing_symbol_reference', 'symbol': symbol,
                                     'file': rel, 'related_files': matches[:12],
                                     'severity': 'review', 'note': 'Inspect references; not proof of duplication'})
            if mode != 'lite':
                related = [str(p.relative_to(self.root)) for p, body in sources.items()
                           if p != path and any(re.search(r'\b' + re.escape(s) + r'\b', body)
                                                for s in symbols if len(s) >= 4)]
                if related:
                    findings.append({'kind': 'impact_candidates', 'file': rel,
                                     'related_files': related[:30], 'severity': 'review'})
        deps = [str(x).strip() for x in proposed_dependencies if str(x).strip()]
        if deps:
            findings.append({'kind': 'dependency_justification_required', 'dependencies': deps,
                             'severity': 'review', 'note': 'Check stdlib and installed alternatives first'})
        if mode == 'ultra':
            findings.append({'kind': 'scope_challenge', 'severity': 'review',
                             'note': 'Confirm each requested feature is necessary and cannot reuse existing code'})
        return {'mode': mode, 'changed_files': sorted(str(p.relative_to(self.root)) for p in changed),
                'files_scanned': len(sources), 'findings': findings,
                'ready_to_merge': False, 'reason': 'advisory only; run security, tests, runtime and independent critic'}

    def debt(self, max_files=3000):
        entries = []
        for path in self._files(max_files=max_files):
            try:
                lines = path.read_text(encoding='utf-8').splitlines()
            except (UnicodeError, OSError):
                continue
            for index, line in enumerate(lines, 1):
                if 'shortcut:' in line:
                    entries.append({'file': str(path.relative_to(self.root)), 'line': index,
                                    'note': line.split('shortcut:', 1)[1].strip()[:300]})
        return entries
