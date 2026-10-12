"""Tests for T1.6 tidy-table logic: sentinel nulling, suffix discovery, masking."""

import numpy as np
import pandas as pd

from hyfuse import qc
from hyfuse.read import (
    SENTINEL_ABS,
    _depths_from_points,
    _discover_suffix,
    _null_sentinel,
)


def test_discover_suffix_prefers_system_and_ignores_tsav():
    cols = [
        "Min1 sTSAS", "Grp1 sTSAS", "Wt1 sTSAS", "Error sTSAS",
        "Min1 uTSAS", "Grp1 uTSAS", "Wt1 uTSAS",
        "Min1 sTSAV", "Grp1 sTSAV", "Wt1 sTSAV",  # must be ignored
    ]
    assert _discover_suffix(cols) == "sTSAS"


def test_discover_suffix_tir_clst():
    cols = ["Min1 sjCLST", "Grp1 sjCLST", "Wt1 sjCLST", "Error sjCLST",
            "Min1 ujCLST", "Grp1 ujCLST", "Wt1 ujCLST"]
    assert _discover_suffix(cols) == "sjCLST"


def test_discover_suffix_none_when_incomplete():
    assert _discover_suffix(["Min1 sTSAS", "Wt1 sTSAS"]) is None  # no Grp1


def test_null_sentinel_replaces_float32_min():
    s = pd.Series([0.5, -3.4028235e38, 1.0, SENTINEL_ABS * 10])
    out = _null_sentinel(s)
    assert out.isna().sum() == 2
    assert out.dropna().tolist() == [0.5, 1.0]


def test_depths_from_points_monotonic_and_covering():
    d = np.array([1.0, 2.0, 4.0])
    frm, to = _depths_from_points(d)
    # intervals are contiguous: to[i] == from[i+1]
    assert np.allclose(to[:-1], frm[1:])
    # centres lie within their intervals
    assert np.all(frm <= d) and np.all(d <= to)


def test_apply_final_mask_keeps_only_ones():
    df = pd.DataFrame({
        "view": ["swir"] * 4,
        "final_mask": [1, 0, 1, 0],
        "depth_from": [0.0, 1.0, 2.0, 3.0],
        "depth_to": [1.0, 2.0, 3.0, 4.0],
    })
    kept = qc.apply_final_mask(df)
    assert len(kept) == 2
    assert (kept["final_mask"] == 1).all()


def test_metres_after_mask():
    df = pd.DataFrame({
        "view": ["tir"] * 3,
        "final_mask": [1, 1, 0],
        "depth_from": [0.0, 1.0, 2.0],
        "depth_to": [1.0, 2.5, 3.0],
    })
    # kept lengths: 1.0 + 1.5 = 2.5 ; masked-off row excluded
    assert qc.metres_after_mask(df) == 2.5


def test_infer_instrument_gen_from_views():
    # R2 F2: instrument_gen derived from present spectral views.
    from types import SimpleNamespace

    from hyfuse.read import infer_instrument_gen

    assert infer_instrument_gen(SimpleNamespace(mir=object(), tir=object())) == "HL4"
    assert infer_instrument_gen(SimpleNamespace(mir=None, tir=object())) == "HL3+"
    assert infer_instrument_gen(SimpleNamespace(mir=None, tir=None)) == "HL2+"
