"""Smoke test to verify test infrastructure works."""


def test_import_kosmos() -> None:
    """Verify the kosmos package is importable."""
    import kosmos

    assert kosmos.__doc__ is not None
