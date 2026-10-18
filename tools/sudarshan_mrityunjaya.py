"""MRITYUNJAYA: non-destructive integrity verification of a local Git checkout.

Checks Git HEAD, staging/worktree status and actual non-ignored working-file
contents. This catches edits that leave porcelain status unchanged.
It never executes a reset or overwrites any user files.
"""
import hashlib
import json
import os
from pathlib import Path

from .sudarshan_execution_contract import AdapterResult
from .sudarshan_worktree import _git

MAX_FILES = 100000
MAX_BYTES = 5_000_000_000


def _content_hash(repository):
    """Hash tracked and untracked non-ignored files, including dirty files."""
    raw = _git('-C',repository,'ls-files','-z','--cached','--others','--exclude-standard')
    names = [name for name in raw.split('\x00') if name]
    if len(names) > MAX_FILES:
        raise ValueError('repository has too many files for bounded integrity verification')
    tree = hashlib.sha256()
    count = 0
    total_bytes = 0
    for name in sorted(set(names)):
        path = (repository / name)
        resolved_parent = path.parent.resolve()
        if resolved_parent != repository and repository not in resolved_parent.parents:
            raise ValueError('repository file path escapes checkout')
        if path.is_symlink():
            value = ('symlink:' + os.readlink(path)).encode('utf-8',errors='surrogateescape')
        elif path.is_file():
            hasher = hashlib.sha256()
            with path.open('rb') as stream:
                while True:
                    block = stream.read(1024*1024)
                    if not block:
                        break
                    total_bytes += len(block)
                    if total_bytes > MAX_BYTES:
                        raise ValueError('repository contents exceed verification limit')
                    hasher.update(block)
            value = ('file:' + hasher.hexdigest()).encode()
        else:
            value = b'absent-or-nonfile'
        tree.update(name.encode('utf-8',errors='surrogateescape'))
        tree.update(b'\x00')
        tree.update(value)
        tree.update(b'\x00')
        count += 1
    return {'sha256': tree.hexdigest(), 'file_count': count}


def baseline(repository):
    repository = Path(repository).resolve(strict=True)
    top = Path(_git('-C',repository,'rev-parse','--show-toplevel').strip()).resolve()
    if top != repository:
        raise ValueError('Git repository root required')
    contents = _content_hash(repository)
    return {'repository':str(repository),
            'head':_git('-C',repository,'rev-parse','HEAD').strip(),
            'status':hashlib.sha256(_git('-C',repository,'status','--porcelain=v1',
                                         '--untracked-files=all').encode()).hexdigest(),
            'content_tree_sha256':contents['sha256'],
            'file_count':contents['file_count'],
            'ignored_files_covered':False}


def verify_baseline(snapshot, *, authorized=False):
    if not authorized:
        raise PermissionError('explicit recovery verification authorization required')
    expected = {'repository','head','status','content_tree_sha256',
                'file_count','ignored_files_covered'}
    if not isinstance(snapshot,dict) or set(snapshot)!=expected:
        raise ValueError('complete content-aware Git baseline required')
    now=baseline(snapshot['repository'])
    matches=(now==snapshot and now['ignored_files_covered'] is False)
    digest=hashlib.sha256(json.dumps(now,sort_keys=True).encode()).hexdigest()
    return AdapterResult('MRITYUNJAYA','passed' if matches else 'failed',
                         'sha256:'+digest if matches else '',
                         ('original Git checkout content unchanged (ignored files excluded)'
                          if matches else 'Git checkout changed; owner recovery required'))
