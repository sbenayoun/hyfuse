"""T2.3 tests: per-view CLR features, zero handling, no view pooling."""

import numpy as np
import pandas as pd

from hyfuse.features import (
    clr,
    clr_features,
    composition_matrix,
    multiplicative_replacement,
)


def _composited():
    # Two windows, two views. SWIR groups {KAOLIN, WHITE-MICA}; TIR {SILICA}.
    # Includes an INVALID group that must be excluded from the composition.
    return pd.DataFrame({
        "hole_id": ["H"] * 5,
        "win_from": [0.0, 0.0, 0.0, 5.0, 5.0],
        "win_to": [5.0, 5.0, 5.0, 10.0, 10.0],
        "view": ["swir", "swir", "tir", "swir", "tir"],
        "mineral_group": ["KAOLIN", "WHITE-MICA", "SILICA", "INVALID", "SILICA"],
        "mean_abundance": [0.6, 0.4, 1.0, 1.0, 0.8],
    })


def test_composition_matrix_is_per_view_and_excludes_invalid():
    comp = _composited()
    sw = composition_matrix(comp, "swir")
    tir = composition_matrix(comp, "tir")
    # SWIR has KAOLIN + WHITE-MICA columns, NO SILICA (that's TIR only).
    assert set(sw.columns) == {"KAOLIN", "WHITE-MICA"}
    assert "SILICA" not in sw.columns
    # TIR has SILICA only; INVALID window (5-10 swir) excluded entirely.
    assert set(tir.columns) == {"SILICA"}
    # The INVALID-only swir window must not appear as a swir composition row.
    assert (5.0, 10.0) not in [(a, b) for (_h, a, b) in sw.index]


def test_multiplicative_replacement_preserves_simplex_and_fills_zeros():
    mat = pd.DataFrame({"A": [0.5, 0.0], "B": [0.5, 1.0]})
    out = multiplicative_replacement(mat, delta=1e-3)
    # rows still sum to 1
    assert np.allclose(out.sum(axis=1), 1.0)
    # the zero in row 1 col A becomes delta
    assert out.iloc[1]["A"] == 1e-3
    assert abs(out.iloc[1]["B"] - (1.0 - 1e-3)) < 1e-12


def test_clr_known_values():
    # equal parts -> clr all zeros (log of equal parts minus the mean = 0)
    mat = pd.DataFrame({"A": [0.25], "B": [0.25], "C": [0.5]})
    out = clr(mat)
    row = out.iloc[0].to_numpy()
    # clr sums to zero by construction
    assert abs(row.sum()) < 1e-12
    # C is twice A and B: clr(C)-clr(A) = ln(0.5/0.25)=ln2
    cols = list(out.columns)
    cC = row[cols.index("C_clr")]
    cA = row[cols.index("A_clr")]
    assert abs((cC - cA) - np.log(2)) < 1e-12


def test_clr_rejects_nonpositive():
    import pytest
    with pytest.raises(ValueError, match="strictly positive"):
        clr(pd.DataFrame({"A": [0.0], "B": [1.0]}))


def test_clr_features_end_to_end_per_view():
    comp = _composited()
    sw = clr_features(comp, "swir", delta=1e-6)
    tir = clr_features(comp, "tir", delta=1e-6)
    # View-prefixed CLR columns: swir groups only / tir groups only.
    assert set(sw.columns) == {"swir_KAOLIN_clr", "swir_WHITE-MICA_clr"}
    assert set(tir.columns) == {"tir_SILICA_clr"}
    # No pooling and no name collision across views.
    assert set(sw.columns).isdisjoint(set(tir.columns))
    # clr rows sum to ~0.
    assert np.allclose(sw.to_numpy().sum(axis=1), 0.0, atol=1e-9)


def test_clr_features_min_nonzero_groups_filter():
    comp = _composited()
    # Require >=2 nonzero groups: TIR windows have only SILICA -> dropped.
    tir = clr_features(comp, "tir", min_nonzero_groups=2)
    assert tir.empty
