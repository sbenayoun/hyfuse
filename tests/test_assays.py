"""T2.2 tests: assay hygiene (below-detection, plausibility flag, wide->long)."""

import numpy as np
import pandas as pd

from hyfuse import qc


def test_resolve_below_detection_halves_abs():
    v = pd.Series([0.5, -0.01, 0.0, -1.0, np.nan])
    resolved, below = qc.resolve_below_detection(v)
    # negatives -> |x|/2 ; non-negatives unchanged
    assert resolved.tolist()[:4] == [0.5, 0.005, 0.0, 0.5]
    assert below.tolist() == [False, True, False, True, False]


def test_flag_implausible_uses_range():
    v = pd.Series([0.1, 200000.0, 50.0, np.nan])
    ranges = {"Au_PPM": [0, 100000]}
    flagged = qc.flag_implausible(v, "Au_PPM", ranges)
    assert flagged.tolist() == [False, True, False, False]


def test_flag_implausible_no_range_never_flags():
    v = pd.Series([1e9, -5.0])
    assert qc.flag_implausible(v, "Cu_PPM", {"Au_PPM": [0, 10]}).tolist() == [False, False]


def test_assays_wide_to_long_resolves_and_flags():
    wide = pd.DataFrame({
        "depth_from": [0.0, 1.0, 2.0],
        "depth_to": [1.0, 2.0, 3.0],
        "Au_PPM": [-0.01, 0.5, 200000.0],   # censored, normal, implausible
        "Cu_PPM": [None, 30.0, 40.0],       # one null -> dropped for that row
    })
    long = qc.assays_wide_to_long(
        wide, "H1",
        plausibility_ppm={"Au_PPM": [0, 100000]},
    )
    au = long[long["element"] == "Au_PPM"].sort_values("depth_from")
    assert au["value"].tolist() == [0.005, 0.5, 200000.0]
    assert au["below_detection"].tolist() == [True, False, False]
    assert au["implausible"].tolist() == [False, False, True]
    # Cu: the null row is dropped, two rows remain
    cu = long[long["element"] == "Cu_PPM"]
    assert len(cu) == 2
    assert set(cu["depth_from"]) == {1.0, 2.0}


def test_assays_wide_to_long_restrict_elements():
    wide = pd.DataFrame({
        "depth_from": [0.0], "depth_to": [1.0],
        "Au_PPM": [1.0], "Cu_PPM": [2.0],
    })
    long = qc.assays_wide_to_long(wide, "H", elements=["Au_PPM"])
    assert set(long["element"]) == {"Au_PPM"}


def test_assays_long_feeds_overlap_join():
    # End-to-end: hygiene output is consumable by the T2.1 compositor.
    from hyfuse.composite import make_windows, overlap_weight_assays
    wide = pd.DataFrame({
        "depth_from": [0.0, 1.0, 2.0, 3.0, 4.0],
        "depth_to": [1.0, 2.0, 3.0, 4.0, 5.0],
        "Au_PPM": [-0.01, 0.2, 0.4, 0.6, 0.8],
    })
    long = qc.assays_wide_to_long(wide, "H", plausibility_ppm={"Au_PPM": [0, 100000]})
    win = make_windows(0.0, 5.0, 5.0, "H")
    out = overlap_weight_assays(win, long)
    # single 5 m window, 5 contiguous 1 m intervals, equal weights:
    # mean(0.005,0.2,0.4,0.6,0.8) = 0.401
    assert abs(float(out["value_wmean"].iloc[0]) - 0.401) < 1e-9
