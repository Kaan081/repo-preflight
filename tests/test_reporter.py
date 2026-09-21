from preflight.reporter import terminal_safe


def test_terminal_safe_escapes_control_characters():
    value = "evil\x1b[31m\nfile\tname"
    result = terminal_safe(value)

    assert "\x1b" not in result
    assert "\n" not in result
    assert "\t" not in result
    assert result == r"evil\x1b[31m\nfile\tname"
