"""Smoke test to verify test infrastructure works."""


def test_import_ummaya() -> None:
    """Verify the ummaya package is importable."""
    import ummaya

    assert ummaya.__doc__ is not None
