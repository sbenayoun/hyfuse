"""T2.5 tests: boundary agreement, tolerance matching, permutation baseline."""

from hyfuse.evaluate import (
    boundary_agreement,
    boundary_agreement_vs_baseline,
    logged_boundaries,
    match_boundaries,
    permutation_baseline,
    prf,
)


def test_logged_boundaries_interior_only():
    # intervals [0,6),[6,10.5),[10.5,13.3) -> edges 0,6,10.5,13.3
    # interior boundaries exclude the top (0) and bottom (13.3): [6, 10.5]
    b = logged_boundaries([0.0, 6.0, 10.5], [6.0, 10.5, 13.3])
    assert b == [6.0, 10.5]


def test_logged_boundaries_single_interval_none():
    assert logged_boundaries([0.0], [10.0]) == []


def test_match_within_tolerance_exact_counts():
    # truth at 10, 20, 30 ; detected at 10.5 (match 10), 21 (match 20), 50 (fp)
    tp, fp, fn = match_boundaries([10.5, 21.0, 50.0], [10.0, 20.0, 30.0], tol=2.0)
    assert (tp, fp, fn) == (2, 1, 1)


def test_match_greedy_one_to_one():
    # two detected near one truth -> only one matches, the other is a FP
    tp, fp, fn = match_boundaries([10.1, 10.2], [10.0], tol=2.0)
    assert (tp, fp, fn) == (1, 1, 0)


def test_prf_values():
    r = prf(tp=2, fp=1, fn=1)
    assert abs(r["precision"] - 2 / 3) < 1e-12
    assert abs(r["recall"] - 2 / 3) < 1e-12
    assert abs(r["f1"] - 2 / 3) < 1e-12


def test_boundary_agreement_perfect():
    r = boundary_agreement([10.0, 20.0], [10.0, 20.0], tol=1.0)
    assert r["precision"] == 1.0 and r["recall"] == 1.0 and r["f1"] == 1.0


def test_permutation_baseline_runs_and_bounded():
    base = permutation_baseline([10.0, 20.0, 30.0], n_detected=3,
                                d0=0.0, d1=100.0, tol=2.0, n=200, seed=1)
    assert 0.0 <= base["f1_mean"] <= 1.0
    assert base["n"] == 200


def test_good_detection_beats_permutation_pvalue_low():
    # Perfect detection of 5 truth boundaries over a long hole -> random draws
    # almost never match as well -> small p-value.
    truth = [20.0, 40.0, 60.0, 80.0, 100.0]
    res = boundary_agreement_vs_baseline(truth, truth, d0=0.0, d1=200.0,
                                         tol=2.0, n_perm=500, seed=1)
    assert res["f1"] == 1.0
    assert res["permutation_p"] < 0.05
    assert res["baseline_f1_mean"] < res["f1"]


def test_random_detection_pvalue_not_significant():
    truth = [20.0, 40.0, 60.0, 80.0, 100.0]
    detected = [7.3, 33.1, 155.0, 190.0, 12.0]  # arbitrary, mostly off
    res = boundary_agreement_vs_baseline(detected, truth, d0=0.0, d1=200.0,
                                         tol=2.0, n_perm=500, seed=2)
    assert res["permutation_p"] > 0.05


def test_snap_to_grid_collapses_fine_boundaries():
    from hyfuse.evaluate import snap_to_grid
    # each boundary snaps to its nearest 5 m grid point:
    # 1->0, 2->0, 3->5 (round(0.6)=1), 11->10  => {0,5,10}
    out = snap_to_grid([1.0, 2.0, 3.0, 11.0], win=5.0, origin=0.0)
    assert out == [0.0, 5.0, 10.0]
    # truly sub-window-spaced points collapse: 0.4,0.6,1.1 all -> 0.0
    assert snap_to_grid([0.4, 0.6, 1.1], win=5.0) == [0.0]


def test_snap_to_grid_ignores_nan():
    import numpy as np

    from hyfuse.evaluate import snap_to_grid
    out = snap_to_grid([5.0, np.nan, 12.0], win=5.0)
    assert out == [5.0, 10.0]


def test_bootstrap_hole_delta_excludes_zero_when_consistent():
    from hyfuse.evaluate import bootstrap_hole_delta
    a = {f"h{i}": 0.5 for i in range(8)}
    b = {f"h{i}": 0.2 for i in range(8)}   # a consistently 0.3 above b
    r = bootstrap_hole_delta(a, b, n=500, seed=1)
    assert r["delta_mean"] == 0.3
    assert r["excludes_zero"] is True


def test_bootstrap_hole_delta_includes_zero_when_noisy():
    from hyfuse.evaluate import bootstrap_hole_delta
    # a and b identical per hole -> delta is exactly 0 -> CI must include zero
    a = {f"h{i}": float(i) for i in range(8)}
    b = {f"h{i}": float(i) for i in range(8)}
    r = bootstrap_hole_delta(a, b, n=500, seed=1)
    assert r["delta_mean"] == 0.0
    assert r["excludes_zero"] is False
