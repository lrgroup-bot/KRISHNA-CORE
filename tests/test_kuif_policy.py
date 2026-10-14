from kuif.policy import PROJECTS, authorize, require_authorized
import pytest


def test_registered_projects_are_read_only():
    assert len(PROJECTS) == 7
    for project in PROJECTS:
        assert authorize(project, 'read')
        assert not authorize(project, 'write', approved=True)


def test_unknown_project_is_denied():
    assert not authorize('unknown', 'read')
    with pytest.raises(PermissionError):
        require_authorized('unknown', 'read')
