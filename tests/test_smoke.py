"""Smoke tests (E0-02). CI passing with zero tests proves nothing."""

from __future__ import annotations

import pytest


def test_package_imports() -> None:
    import thesis

    assert thesis.__name__ == "thesis"


@pytest.mark.slow
def test_slow_marker_is_deselected_in_ci() -> None:
    """Shows in the CI log as deselected, proving `slow` tests stay out of CI (record §6.9)."""
