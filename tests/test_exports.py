"""Tests for expardus_tracing package-level exports and __all__."""
from __future__ import annotations

import expardus_tracing


class TestAllExports:
    """Verify __all__ is complete and every listed symbol is importable."""

    def test_all_symbols_importable(self):
        """Every name in __all__ must exist on the module."""
        for name in expardus_tracing.__all__:
            assert hasattr(expardus_tracing, name), (
                f"__all__ lists '{name}' but it is not importable from expardus_tracing"
            )

    def test_all_public_symbols_listed(self):
        """Every public (non-underscore) attribute should appear in __all__."""
        public_attrs = {
            name
            for name in dir(expardus_tracing)
            if not name.startswith("_")
            and not name == "os"  # stdlib import, not our symbol
            and not name == "annotations"  # from __future__
        }
        all_set = set(expardus_tracing.__all__)
        missing = public_attrs - all_set
        # Filter out sub-module names (context, w3c, headers, logging, celery)
        submodules = {"context", "w3c", "headers", "logging", "celery"}
        missing -= submodules
        assert not missing, (
            f"Public symbols not in __all__: {missing}"
        )

    def test_no_duplicates_in_all(self):
        """__all__ should not contain duplicate entries."""
        assert len(expardus_tracing.__all__) == len(set(expardus_tracing.__all__))
