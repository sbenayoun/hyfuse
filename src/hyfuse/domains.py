"""domains.py (T2.4): per-view domaining.

Pipeline per view, on the CLR feature matrix (features.clr_features):
  1. PCA (whiten-ish via standardisation first) -> low-dim scores.
  2. HDBSCAN on the scores (record params); labels + soft membership strengths.
  3. Depth-aware segmentation with `ruptures` on the PCA scores, enforcing a
     minimum interval length, to produce contiguous DOMAIN boundaries down-hole.
Also a PCA + k-means baseline (the common method a GSWA geologist named), so
results are compared with the standard approach, not only with each other.

Determinism: every stochastic step takes `seed` (params.yaml seed), addressing
the R1 F4 finding that the seed was previously inert.

Output per hole/view: a DataFrame of windows with pca scores, cluster label,
membership strength, and a `domain` id (contiguous segment index); plus the list
of boundary depths.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import ruptures as rpt
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


@dataclass
class DomainResult:
    """Per-view domaining output for one hole."""

    windows: pd.DataFrame          # index (hole_id,win_from,win_to) + outputs
    boundaries: list[float]        # depths (win_from) where a new domain starts
    n_components: int
    params: dict = field(default_factory=dict)


def _pca_scores(x: np.ndarray, n_components: int, seed: int) -> np.ndarray:
    n_comp = max(1, min(n_components, x.shape[1], x.shape[0]))
    xs = StandardScaler().fit_transform(x)
    return PCA(n_components=n_comp, random_state=seed).fit_transform(xs)


def _segment_boundaries(scores: np.ndarray, win_from: np.ndarray,
                        min_size: int, penalty: float) -> list[float]:
    """Depth-ordered change-point segmentation on PCA scores (ruptures PELT).

    min_size is in windows (>=1). Returns the win_from depths that start a new
    segment (excluding the very first window). Deterministic (no randomness).
    """
    n = scores.shape[0]
    if n <= max(2, min_size):
        return []
    algo = rpt.Pelt(model="rbf", min_size=max(1, min_size)).fit(scores)
    # bkps are indices AFTER each segment end; last is n.
    bkps = algo.predict(pen=penalty)
    starts = [b for b in bkps if 0 < b < n]
    return [float(win_from[i]) for i in starts]


def domain_view(features: pd.DataFrame, *, seed: int = 42,
                n_components: int = 3, min_cluster_size: int = 5,
                min_interval_windows: int = 2,
                seg_penalty: float = 3.0) -> DomainResult:
    """Domaining for a single view's CLR feature matrix.

    features: index (hole_id, win_from, win_to), CLR columns. Must be depth-sorted
    within a hole (caller ensures a single hole).
    """
    params = {
        "seed": seed, "n_components": n_components,
        "min_cluster_size": min_cluster_size,
        "min_interval_windows": min_interval_windows,
        "seg_penalty": seg_penalty, "pca_standardised": True,
        "hdbscan": "sklearn.cluster.HDBSCAN", "segmenter": "ruptures.Pelt(rbf)",
    }

    out = features.copy().sort_index(level="win_from")
    if out.empty:
        return DomainResult(out, [], 0, params)

    x = out.to_numpy(dtype=float)
    scores = _pca_scores(x, n_components, seed)
    for j in range(scores.shape[1]):
        out[f"pc{j + 1}"] = scores[:, j]

    # HDBSCAN clustering (soft membership via probabilities_).
    n = scores.shape[0]
    mcs = max(2, min(min_cluster_size, n))
    hdb = HDBSCAN(min_cluster_size=mcs, copy=True)
    labels = hdb.fit_predict(scores)
    out["cluster"] = labels
    out["membership"] = getattr(hdb, "probabilities_",
                                np.full(n, np.nan))

    # Depth-aware contiguous domains via change-point segmentation.
    win_from = out.index.get_level_values("win_from").to_numpy(dtype=float)
    boundaries = _segment_boundaries(scores, win_from,
                                     min_interval_windows, seg_penalty)
    # Assign a contiguous domain id by walking boundaries in depth order.
    domain_id = np.zeros(n, dtype=int)
    cur = 0
    bset = set(boundaries)
    for i in range(n):
        if i > 0 and float(win_from[i]) in bset:
            cur += 1
        domain_id[i] = cur
    out["domain"] = domain_id

    return DomainResult(out, boundaries, scores.shape[1], params)


def kmeans_baseline(features: pd.DataFrame, *, seed: int = 42,
                    n_components: int = 3, k: int = 4) -> pd.DataFrame:
    """PCA + k-means baseline (the common spectral-clustering approach).

    Returns the features frame with a 'kmeans' label column added.
    """
    out = features.copy().sort_index(level="win_from")
    if out.empty:
        out["kmeans"] = []
        return out
    x = out.to_numpy(dtype=float)
    scores = _pca_scores(x, n_components, seed)
    kk = max(1, min(k, scores.shape[0]))
    km = KMeans(n_clusters=kk, random_state=seed, n_init=10)
    out["kmeans"] = km.fit_predict(scores)
    return out
