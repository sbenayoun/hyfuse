"""T2.1 tests: windowing, mineral compositing, overlap-weighted assay join.

The overlap-weighted join is checked EXACTLY on a hand-built mini hole where an
assay interval straddles a window boundary, so blind averaging would give a
different answer than overlap weighting.
"""

import pandas as pd

from hyfuse.composite import (
    composite_minerals,
    make_windows,
    overlap_weight_assays,
)


def test_make_windows_basic():
    w = make_windows(0.0, 10.0, 5.0, "H1")
    assert list(w["win_from"]) == [0.0, 5.0]
    assert list(w["win_to"]) == [5.0, 10.0]
    assert (w["hole_id"] == "H1").all()


def test_make_windows_last_window_clipped():
    w = make_windows(0.0, 7.0, 5.0)
    # two windows: [0,5), [5,7) clipped to the hole end
    assert list(w["win_from"]) == [0.0, 5.0]
    assert list(w["win_to"]) == [5.0, 7.0]


def test_make_windows_empty_when_degenerate():
    assert make_windows(5.0, 5.0, 5.0).empty


def test_composite_minerals_midpoint_membership():
    # Two swir samples: mids 1.0 and 6.0 -> fall in windows [0,5) and [5,10).
    tidy = pd.DataFrame({
        "hole_id": ["H"] * 3,
        "depth_from": [0.5, 1.0, 5.5],
        "depth_to": [1.5, 2.0, 6.5],
        "view": ["swir", "swir", "swir"],
        "mineral_group": ["KAOLIN", "KAOLIN", "SILICA"],
        "abundance": [0.4, 0.6, 1.0],
        "final_mask": [1, 1, 1],
    })
    out = composite_minerals(tidy, win=5.0)
    # Windows anchored at origin 0 (collar), so [0,5) and [5,10):
    #   window [0,5) KAOLIN: mean(0.4,0.6)=0.5 n=2 (sample mids 1.0, 1.5)
    #   window [5,6.5) SILICA: 1.0 n=1 (sample mid 6.0)
    k = out[(out["win_from"] == 0.0) & (out["mineral_group"] == "KAOLIN")]
    s = out[(out["win_from"] == 5.0) & (out["mineral_group"] == "SILICA")]
    assert float(k["mean_abundance"].iloc[0]) == 0.5
    assert int(k["n_samples"].iloc[0]) == 2
    assert float(s["mean_abundance"].iloc[0]) == 1.0


def test_composite_minerals_excludes_masked_off():
    tidy = pd.DataFrame({
        "hole_id": ["H"] * 2,
        "depth_from": [1.0, 2.0],
        "depth_to": [1.1, 2.1],
        "view": ["tir", "tir"],
        "mineral_group": ["SILICA", "SILICA"],
        "abundance": [1.0, 0.0],
        "final_mask": [1, 0],   # second row masked off -> excluded
    })
    out = composite_minerals(tidy, win=5.0)
    row = out[out["mineral_group"] == "SILICA"].iloc[0]
    assert int(row["n_samples"]) == 1
    assert float(row["mean_abundance"]) == 1.0


def test_overlap_weighted_assay_exact():
    # One window [0,5). Two assay intervals:
    #   A: [0,4) value 10  -> overlap 4
    #   B: [3,8) value 20  -> overlap with window = min(5,8)-max(0,3)=2
    # overlap-weighted mean = (10*4 + 20*2) / (4+2) = 80/6 = 13.3333...
    # (blind mean would be (10+20)/2 = 15, which is WRONG.)
    windows = pd.DataFrame({"hole_id": ["H"], "win_from": [0.0], "win_to": [5.0]})
    assays = pd.DataFrame({
        "hole_id": ["H", "H"],
        "depth_from": [0.0, 3.0],
        "depth_to": [4.0, 8.0],
        "element": ["Au_PPM", "Au_PPM"],
        "value": [10.0, 20.0],
    })
    out = overlap_weight_assays(windows, assays)
    assert len(out) == 1
    row = out.iloc[0]
    assert row["element"] == "Au_PPM"
    assert abs(float(row["value_wmean"]) - (80.0 / 6.0)) < 1e-9
    assert float(row["total_overlap"]) == 6.0


def test_overlap_weighted_no_overlap_excluded():
    # Assay interval entirely outside the window -> no row emitted.
    windows = pd.DataFrame({"hole_id": ["H"], "win_from": [0.0], "win_to": [5.0]})
    assays = pd.DataFrame({
        "hole_id": ["H"],
        "depth_from": [10.0], "depth_to": [12.0],
        "element": ["Au_PPM"], "value": [99.0],
    })
    assert overlap_weight_assays(windows, assays).empty


def test_overlap_touching_boundary_is_zero_overlap():
    # Interval [5,9) touches window [0,5) only at the boundary -> overlap 0.
    windows = pd.DataFrame({"hole_id": ["H"], "win_from": [0.0], "win_to": [5.0]})
    assays = pd.DataFrame({
        "hole_id": ["H"],
        "depth_from": [5.0], "depth_to": [9.0],
        "element": ["As_PPM"], "value": [7.0],
    })
    assert overlap_weight_assays(windows, assays).empty
