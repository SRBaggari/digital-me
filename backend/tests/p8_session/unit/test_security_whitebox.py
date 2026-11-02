from digital_me.server.security import DEV_FRONTEND_PORT, allowed_origins, is_origin_allowed


def test_allowed_origins_cover_app_and_dev_ports():
    origins = allowed_origins(8765)
    assert "http://localhost:8765" in origins
    assert f"http://127.0.0.1:{DEV_FRONTEND_PORT}" in origins
    assert "http://[::1]:8765" in origins
    assert len(origins) == 6


def test_origin_normalised_before_comparison():
    assert is_origin_allowed(" HTTP://LOCALHOST:8765/ ", 8765)


def test_missing_origin_allowed_for_local_tools():
    assert is_origin_allowed(None, 8765)
