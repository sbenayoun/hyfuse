"""Smoke test so `make test` has something to run from T1.1 onward."""

import hyfuse


def test_version():
    assert hyfuse.__version__ == "0.1.0"


def test_imports():
    # Core modules import without side effects.
    from hyfuse import (  # noqa: F401
        domains,
        evaluate,
        features,
        fetch,
        fusion,
        qc,
        read,
        synth,
    )
