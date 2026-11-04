"""Read-only local component health checks."""
import socket

def tcp_reachable(host: str = "127.0.0.1", port: int = 11434, timeout: float = 1.0) -> bool:
    if host not in {"127.0.0.1", "localhost"} or not (1 <= port <= 65535):
        raise ValueError("Only local health checks are allowed")
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
