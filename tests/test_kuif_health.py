import pytest
from kuif.health import tcp_reachable

def test_nonlocal_rejected():
    with pytest.raises(ValueError):
        tcp_reachable("example.com")

def test_invalid_port_rejected():
    with pytest.raises(ValueError):
        tcp_reachable(port=0)
