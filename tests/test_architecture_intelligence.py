from pathlib import Path

import pytest

from core.architecture_intelligence import ArchifyPolicy, archify_environment


def test_update_check_is_forced_off():
    assert archify_environment({})["ARCHIFY_UPDATE_CHECK_DISABLED"] == "1"


def test_privileged_actions_fail_closed():
    policy = ArchifyPolicy()
    for action in ("repo-write", "merge", "deploy", "spend", "approve"):
        with pytest.raises(PermissionError):
            policy.assert_no_privileged_action(action)


def test_output_cannot_be_repo_root_or_protected_source(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "core").mkdir(parents=True)
    policy = ArchifyPolicy()
    with pytest.raises(ValueError):
        policy.assert_safe_paths(repo, repo)
    with pytest.raises(ValueError):
        policy.assert_safe_paths(repo, repo / "core" / "archify")


def test_dedicated_generated_output_is_allowed(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "generated-architecture"
    policy = ArchifyPolicy()
    policy.assert_safe_paths(repo, out)
