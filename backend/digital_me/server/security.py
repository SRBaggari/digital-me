"""Local-only access rules.

* Host allowlist: blocks DNS-rebinding, where a website makes your browser talk to 127.0.0.1
  under its own domain name.
* WebSocket Origin allowlist: blocks other websites open in your browser from connecting.
"""

from __future__ import annotations

LOCAL_HOSTNAMES = ["localhost", "127.0.0.1", "[::1]", "::1"]
DEV_FRONTEND_PORT = 5173


def allowed_origins(server_port: int) -> frozenset[str]:
    return frozenset(
        f"http://{host}:{port}"
        for port in (server_port, DEV_FRONTEND_PORT)
        for host in ("localhost", "127.0.0.1", "[::1]")
    )


def is_origin_allowed(origin: str | None, server_port: int) -> bool:
    """Browsers always send Origin on WebSocket upgrades; non-browser local tools may omit it."""
    if origin is None:
        return True
    return origin.strip().lower().rstrip("/") in allowed_origins(server_port)
