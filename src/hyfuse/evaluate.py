"""evaluate.py (T2.5, T2.6, T3.3): scoring on held-out splits.

T2.5 boundary agreement (pre-registered in params.yaml, frozen before results):
- Score DETECTED domain boundaries against LOGGED rock-type interval boundaries
  (wamex_dh_geology edges), matching within a depth tolerance. We score
  BOUNDARIES, not lithology-code equality (codes are company-specific).
- Metric: precision / recall / F1 within tolerance (greedy 1-1 matching).
- Permutation baseline: random boundaries with the SAME COUNT per hole, drawn
  within the hole's depth range, repeated n times -> baseline F1 distribution.

T2.6 confounders and T3.3 full ablation are added later.
"""

from __future__ import annotations

import numpy as np


def logged_boundaries(from_depth, to_depth) -> list[float]:
    """Interior boundaries from contiguous logged intervals.

    The boundary set is the sorted unique interval edges, excluding the overall
    top and bottom (those are hole ends, not geological boundaries).
    """
    edges = sorted(set(np.r_[np.asarray(from_depth, float),
                             np.asarray(to_depth, float)].tolist()))
    if len(edges) <= 2:
        return []
    return edges[1:-1]


def match_boundaries(detected, truth, tol: float) -> tuple[int, int, int]:
    """Greedy one-to-one matching within tolerance.

    Returns (tp, fp, fn): true positives (a detected boundary within tol of an
    unused truth boundary), false positives (detected, unmatched), false
    negatives (truth, unmatched).
    """
    det = sorted(float(x) for x in detected)
    tru = sorted(float(x) for x in truth)
    used = [False] * len(tru)
    tp = 0
    for d in det:
        best, best_j = tol + 1e-9, -1
        for j, t in enumerate(tru):
            if used[j]:
                continue
            dist = abs(d - t)
            if dist <= tol and dist < best:
                best, best_j = dist, j
        if best_j >= 0:
            used[best_j] = True
            tp += 1
    fp = len(det) - tp
    fn = len(tru) - sum(used)
    return tp, fp, fn


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    """Precision / recall / F1 from counts (0 when undefined)."""
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn}


def boundary_agreement(detected, truth, tol: float) -> dict[str, float]:
    """Precision/recall/F1 of detected vs truth boundaries within tolerance."""
    tp, fp, fn = match_boundaries(detected, truth, tol)
    return prf(tp, fp, fn)


def permutation_baseline(truth, n_detected: int, d0: float, d1: float,
                         tol: float, *, n: int = 1000,
                         seed: int = 42) -> dict[str, float]:
    """Random-boundary baseline: draw n_detected boundaries in [d0,d1], score vs
    truth, repeat n times. Returns mean/std and a one-sided p-value proxy
    (fraction of random F1 >= a reference, filled by the caller if needed).
    """
    rng = np.random.default_rng(seed)
    tru = [float(x) for x in truth]
    if n_detected <= 0 or d1 <= d0:
        return {"f1_mean": 0.0, "f1_std": 0.0, "f1_p95": 0.0, "n": n}
    f1s = np.empty(n)
    for i in range(n):
        rand = rng.uniform(d0, d1, size=n_detected)
        tp, fp, fn = match_boundaries(rand, tru, tol)
        f1s[i] = prf(tp, fp, fn)["f1"]
    return {"f1_mean": float(f1s.mean()), "f1_std": float(f1s.std()),
            "f1_p95": float(np.percentile(f1s, 95)), "n": n}


def boundary_agreement_vs_baseline(detected, truth, d0: float, d1: float,
                                   tol: float, *, n_perm: int = 1000,
                                   seed: int = 42) -> dict[str, float]:
    """Observed boundary F1 plus the permutation-baseline distribution and a
    one-sided p-value (fraction of random draws with F1 >= observed)."""
    obs = boundary_agreement(detected, truth, tol)
    base = permutation_baseline(truth, len(list(detected)), d0, d1, tol,
                                n=n_perm, seed=seed)
    # p-value: how often random boundaries match truth at least as well.
    rng = np.random.default_rng(seed)
    tru = [float(x) for x in truth]
    nd = len(list(detected))
    ge = 0
    if nd > 0 and d1 > d0:
        for _ in range(n_perm):
            rand = rng.uniform(d0, d1, size=nd)
            tp, fp, fn = match_boundaries(rand, tru, tol)
            if prf(tp, fp, fn)["f1"] >= obs["f1"]:
                ge += 1
        pval = (ge + 1) / (n_perm + 1)
    else:
        pval = 1.0
    return {**obs,
            "baseline_f1_mean": base["f1_mean"],
            "baseline_f1_p95": base["f1_p95"],
            "permutation_p": pval}
