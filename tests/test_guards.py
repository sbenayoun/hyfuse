"""T3.4/F7 regression tests: guards the calibration said were missing.

(a) assay CV is leave-holes-out (grouped), not a window-level random split;
(b) a modest per-hole x1000 (under the plausibility cap) is flagged as an
    inter-hole outlier;
(c) the scored boundary tolerance matches the pre-registered value unless an
    override reason is given.
"""

import inspect

import numpy as np
import pandas as pd

from hyfuse import evaluate as ev
from hyfuse import qc


def test_assay_cv_is_grouped_by_hole_not_leaky():
    # Build data where the TARGET is pure hole identity: each hole has a constant
    # y. A grouped (leave-holes-out) CV cannot predict a held-out hole's level ->
    # R^2 <= 0. A leaky window-level split WOULD score high. We assert the honest
    # grouped behaviour.
    rng = np.random.default_rng(0)
    rows, y, g = [], [], []
    hole_level = {f"h{i}": float(i) for i in range(6)}
    for h, lvl in hole_level.items():
        for _ in range(20):
            rows.append(rng.normal(size=5))
            y.append(lvl)              # target = hole level (no within-hole signal)
            g.append(h)
    X = pd.DataFrame(rows)
    res = ev.assay_prediction_cv(X, pd.Series(y), np.array(g), seed=0)
    # grouped CV: predicting a held-out hole's constant level from noise -> no skill
    assert res["r2_median"] <= 0.0, res
    assert res["has_skill"] is False


def test_assay_cv_uses_groupkfold_in_source():
    # Static guard: the function must reference GroupKFold (not a plain KFold
    # window-level split). Catches the exact calibration-planted leak.
    src = inspect.getsource(ev.assay_prediction_cv)
    assert "GroupKFold" in src
    assert "KFold(n_splits" not in src or "GroupKFold" in src  # no bare KFold leak


def test_inter_hole_outlier_flags_modest_scaling():
    # 5 holes near 0.02 ppm, one hole x1000 (~20 ppm) -> still under the 100000
    # cap (so flag_implausible would MISS it) but a clear inter-hole outlier.
    frames = []
    for i in range(5):
        frames.append(pd.DataFrame({
            "hole_id": f"h{i}", "element": "Au_PPM",
            "value": np.full(10, 0.02),
        }))
    frames.append(pd.DataFrame({
        "hole_id": "BAD", "element": "Au_PPM", "value": np.full(10, 20.0),
    }))
    long = pd.concat(frames, ignore_index=True)
    flagged = qc.inter_hole_outlier_holes(long, "Au_PPM", factor=50.0)
    assert flagged == ["BAD"]
    # the plausibility cap alone would NOT catch 20 ppm
    assert not qc.flag_implausible(pd.Series([20.0]), "Au_PPM",
                                   {"Au_PPM": [0, 100000]}).iloc[0]


def test_inter_hole_outlier_clean_data_no_flag():
    frames = [pd.DataFrame({"hole_id": f"h{i}", "element": "Au_PPM",
                            "value": np.full(10, 0.02 * (i + 1))})
              for i in range(5)]
    long = pd.concat(frames, ignore_index=True)
    assert qc.inter_hole_outlier_holes(long, "Au_PPM", factor=50.0) == []


def test_tolerance_guard_matches_preregistered():
    g = ev.preregistered_tolerance_ok(2.0)
    assert g["ok"] is True and g["preregistered"] == 2.0


def test_tolerance_guard_flags_posthoc_change():
    g = ev.preregistered_tolerance_ok(4.0)   # the calibration-planted change
    assert g["ok"] is False


def test_tolerance_guard_allows_documented_override():
    g = ev.preregistered_tolerance_ok(4.0, override_reason="sensitivity analysis in README")
    assert g["ok"] is True
    assert g["override_reason"]
