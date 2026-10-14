from kuif.identity import Principal, can_access

def test_scoped_principal():
    user = Principal("user-1", frozenset({"krishna"}), frozenset({"read"}))
    assert can_access(user, "krishna", "read")
    assert not can_access(user, "kuber", "read")
    assert not can_access(user, "krishna", "analyze")
    assert not can_access(user, "krishna", "write")

def test_anonymous_denied():
    assert not can_access(Principal("", frozenset({"krishna"}), frozenset({"read"})), "krishna", "read")
