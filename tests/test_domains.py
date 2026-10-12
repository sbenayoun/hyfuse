"""T2.4 tests: per-view domaining — determinism, boundary detection, baseline."""

import numpy as np
import pandas as pd

from hyfuse.domains import domain_view, kmeans_baseline


def _two_block_features(n=40, seed=0):
    """Synthetic CLR-like features: two depth blocks with distinct means.

    First half centred at one point, second half at another -> a single true
    boundary near the middle.
    """
    rng = np.random.default_rng(seed)
    half = n // 2
    a = rng.normal(loc=[2.0, -2.0, 0.0], scale=0.2, size=(half, 3))
    b = rng.normal(loc=[-2.0, 2.0, 0.0], scale=0.2, size=(n - half, 3))
    x = np.vstack([a, b])
    win_from = np.arange(n, dtype=float) * 5.0
    idx = pd.MultiIndex.from_arrays(
        [["H"] * n, win_from, win_from + 5.0],
        names=["hole_id", "win_from", "win_to"],
    )
    return pd.DataFrame(x, index=idx,
                        columns=["g1_clr", "g2_clr", "g3_clr"])


def test_domain_view_is_deterministic():
    feats = _two_block_features()
    r1 = domain_view(feats, seed=42)
    r2 = domain_view(feats, seed=42)
    assert r1.windows["domain"].tolist() == r2.windows["domain"].tolist()
    assert r1.boundaries == r2.boundaries
    assert r1.windows["cluster"].tolist() == r2.windows["cluster"].tolist()


def test_domain_view_detects_mid_boundary():
    feats = _two_block_features(n=40)
    r = domain_view(feats, seed=42, min_interval_windows=3, seg_penalty=2.0)
    # true change at window 20 -> depth 100.0; expect a boundary within +/- 2 win.
    assert r.boundaries, "no boundary detected on a clear two-block signal"
    nearest = min(r.boundaries, key=lambda d: abs(d - 100.0))
    assert abs(nearest - 100.0) <= 10.0  # within two 5 m windows
    # at least two contiguous domains result
    assert r.windows["domain"].nunique() >= 2


def test_domain_view_records_params_and_scores():
    feats = _two_block_features()
    r = domain_view(feats, seed=7, n_components=2)
    assert r.params["seed"] == 7
    assert r.n_components == 2
    assert {"pc1", "pc2", "cluster", "membership", "domain"} <= set(r.windows.columns)


def test_domain_view_empty():
    empty = pd.DataFrame(
        columns=["g1_clr"],
        index=pd.MultiIndex.from_arrays([[], [], []],
                                        names=["hole_id", "win_from", "win_to"]),
    )
    r = domain_view(empty, seed=1)
    assert r.windows.empty and r.boundaries == []


def test_kmeans_baseline_deterministic_and_labelled():
    feats = _two_block_features()
    a = kmeans_baseline(feats, seed=42, k=2)
    b = kmeans_baseline(feats, seed=42, k=2)
    assert "kmeans" in a.columns
    assert a["kmeans"].tolist() == b["kmeans"].tolist()
    # two well-separated blocks -> two clusters actually used
    assert a["kmeans"].nunique() == 2
