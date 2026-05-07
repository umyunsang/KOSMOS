"""Smoke test to verify test infrastructure works."""


def test_import_kosax() -> None:
    """Verify the kosax package is importable."""
    import kosax

    assert kosax.__doc__ is not None
