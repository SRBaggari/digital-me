def test_binary_content_is_not_scanned(guard):
    data = b"\0\0" + b"sk-" + b"a" * 40
    assert guard.check(["image.png"], lambda p: data) == []


def test_oversize_content_is_not_scanned(guard):
    data = b"sk-" + b"a" * (guard.MAX_TEXT_BYTES + 1)
    assert guard.check(["big.txt"], lambda p: data) == []


def test_deleted_file_is_skipped(guard):
    assert guard.check(["gone.py"], lambda p: None) == []


def test_windows_separators_normalised(guard):
    assert guard.path_problem("instances\\alice\\profile.yaml")


def test_instances_directory_itself_blocked(guard):
    assert guard.path_problem("instances")


def test_path_problem_short_circuits_content_scan(guard):
    calls = []
    guard.check(["a.wav"], lambda p: calls.append(p))
    assert calls == []


def test_short_quoted_values_not_flagged(guard):
    assert guard.content_problems('password = "short"') == []
