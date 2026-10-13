"""evaluate.py (T2.5, T2.6, T3.3): scoring on held-out splits.

T2.5 boundary agreement (pre-registered in params.yaml, frozen before results):
- Score DETECTED domain boundaries against LOGGED rock-type interval boundaries
  (wamex_dh_geology edges), matching within a depth tolerance. We score
  BOUNDARIES, not lithology-code equality (codes are company-specific).
- Metric: precision / recall / F1 within tolerance (greedy 1-1 matching).
- Permutation baseline: random boundaries with the SAME COUNT per hole, drawn
  within the hole's depth range, repeated n times -> baseline F1 distribution.

T2.6 confounder check:
- Does the domain/cluster assignment predict processing_level or instrument_gen
  better than chance? If yes, "geological domains" is NOT supported without more
  controls. Tested with a GROUPED (by hole) cross-validated classifier and
  mutual information, each against a label-shuffle baseline.

T3.3 full ablation is added later.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mutual_info_score
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

log = logging.getLogger("hyfuse.evaluate")


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


def snap_to_grid(boundaries, win: float, origin: float = 0.0) -> list[float]:
    """Snap boundaries to the window grid (resolution floor) and dedupe.

    Logged lithology is often far finer than the window size; the pipeline
    cannot resolve boundaries below `win`. Snapping both logged and detected
    boundaries to grid-cell starts makes the comparison fair at our resolution
    and collapses sub-window-spaced logged boundaries to the windows they fall
    in (this is the 'logging density' adjustment the plan calls for)."""
    if win <= 0:
        return sorted({float(b) for b in boundaries if np.isfinite(b)})
    snapped = {origin + round((float(b) - origin) / win) * win
               for b in boundaries if np.isfinite(b)}
    return sorted(snapped)


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


# --------------------------------------------------------------------------- #
# T2.6 confounder check
# --------------------------------------------------------------------------- #

def _n_groups_splits(groups) -> int:
    n_groups = len(set(groups))
    return max(2, min(5, n_groups))


def confounder_mutual_information(labels, confounder) -> dict[str, float]:
    """Mutual information between cluster/domain labels and a confounder.

    Returns observed MI and a shuffle baseline (mean MI over label shuffles) so
    MI can be read against chance. High observed-vs-baseline MI means the
    clustering is partly explained by the confounder.
    """
    labels = np.asarray(labels)
    conf = np.asarray(confounder)
    obs = float(mutual_info_score(labels, conf))
    rng = np.random.default_rng(42)
    shuffles = np.empty(200)
    for i in range(200):
        shuffles[i] = mutual_info_score(rng.permutation(labels), conf)
    return {"mi": obs, "mi_shuffle_mean": float(shuffles.mean()),
            "mi_shuffle_p95": float(np.percentile(shuffles, 95))}


def confounder_classifier_auc(features: np.ndarray, confounder,
                              groups, *, seed: int = 42) -> dict[str, float]:
    """Grouped CV: can a classifier predict the confounder from the domain
    features better than chance?

    Uses GroupKFold by hole so hole identity does not leak. Returns mean
    cross-validated accuracy and the majority-class rate (chance baseline). If
    mean accuracy >> majority rate, the features encode the confounder.
    Degenerate cases (one class, too few groups) return chance = accuracy.
    """
    y = np.asarray(confounder)
    g = np.asarray(groups)
    x = np.asarray(features, dtype=float)
    classes, counts = np.unique(y, return_counts=True)
    majority = float(counts.max() / counts.sum())
    out = {"cv_accuracy": majority, "majority_rate": majority,
           "n_classes": len(classes), "n_groups": len(set(g.tolist()))}
    if len(classes) < 2 or out["n_groups"] < 2 or x.shape[0] < 4:
        out["note"] = "degenerate (single class / too few groups); chance only"
        return out
    n_splits = _n_groups_splits(g)
    # Scaler INSIDE the CV pipeline so it is fit on each training fold only
    # (R2 finding F1: fitting the scaler on the full matrix before the split is
    # a leakage pattern; a Pipeline fits it per fold).
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, random_state=seed)),
    ])
    try:
        scores = cross_val_score(pipe, x, y, groups=g,
                                 cv=GroupKFold(n_splits=n_splits),
                                 scoring="accuracy")
        out["cv_accuracy"] = float(scores.mean())
        out["cv_accuracy_std"] = float(scores.std())
    except ValueError as exc:
        out["note"] = f"cv failed: {exc}"
    return out


def confounder_report(labels, features, confounders: dict,
                      groups, *, seed: int = 42) -> dict[str, dict]:
    """Run MI + grouped-classifier checks for each named confounder.

    confounders: {name: array-like of per-window confounder values}
    (e.g. {'processing_level': [...], 'instrument_gen': [...]}).
    Returns {name: {mi..., cv_accuracy..., flag_confounded: bool}}. flag=True
    requires the GROUPED CLASSIFIER to beat the majority-class rate by a margin
    (the robust signal). MI is reported as corroboration but does NOT flag on its
    own: with imbalanced confounder classes, MI can exceed its shuffle p95 by
    chance even when the classifier is at/below chance (calibration finding) — so
    MI-only flags are false positives and are avoided.
    """
    report: dict[str, dict] = {}
    for name, conf in confounders.items():
        mi = confounder_mutual_information(labels, conf)
        auc = confounder_classifier_auc(features, conf, groups, seed=seed)
        # primary signal: classifier clearly beats chance (majority rate).
        classifier_beats_chance = auc["cv_accuracy"] > auc["majority_rate"] + 0.10
        mi_elevated = mi["mi"] > mi["mi_shuffle_p95"] and mi["mi"] > 0.05
        flag = classifier_beats_chance
        report[name] = {**mi, **auc, "flag_confounded": bool(flag),
                        "mi_elevated": bool(mi_elevated)}
    return report


# --------------------------------------------------------------------------- #
# T3.3 assay-target prediction (leave-holes-out) + hole-level bootstrap
# --------------------------------------------------------------------------- #

def assay_prediction_cv(features: pd.DataFrame, target: pd.Series,
                        groups, *, seed: int = 42,
                        n_splits: int = 5) -> dict[str, float]:
    """Leave-holes-out CV R^2 for predicting an assay target from arm features.

    GroupKFold by hole; a StandardScaler+Ridge pipeline inside the CV (stable in
    the small-sample / near-constant-column regime where HistGBR fails). Returns
    mean/std CV R^2 and n. log1p-transforms the non-negative, skewed target.
    """
    x = features.to_numpy(dtype=float)
    y = np.log1p(np.asarray(target, dtype=float).clip(min=0))
    g = np.asarray(groups)
    n_groups = len(set(g.tolist()))
    out = {"n": len(y), "n_groups": n_groups}
    if n_groups < 2 or len(y) < 10:
        out["note"] = "too few holes/rows for grouped CV"
        out["r2_mean"] = float("nan")
        return out
    k = max(2, min(n_splits, n_groups))
    # Strong regularisation: features are many and collinear vs few holes, so a
    # weakly-regularised fit overfits per fold and gives absurd negative R^2.
    # alpha=100 is an honest ridge for this p-vs-n regime (reported, not tuned to
    # a target). RidgeCV over a small grid would be a later refinement.
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=100.0)),
    ])
    try:
        scores = cross_val_score(model, x, y, groups=g,
                                 cv=GroupKFold(n_splits=k), scoring="r2")
        out["r2_mean"] = float(scores.mean())
        out["r2_median"] = float(np.median(scores))
        out["r2_std"] = float(scores.std())
        out["r2_folds"] = [float(s) for s in scores]
        # honest skill flag: positive median R^2 across held-out holes
        out["has_skill"] = bool(np.median(scores) > 0)
    except ValueError as exc:
        out["note"] = f"cv failed: {exc}"
        out["r2_mean"] = float("nan")
    return out


def bootstrap_hole_delta(per_hole_a: dict[str, float],
                         per_hole_b: dict[str, float], *,
                         n: int = 1000, seed: int = 42) -> dict[str, float]:
    """Hole-level bootstrap of the mean difference (arm_a - arm_b) of a per-hole
    metric. Resamples HOLES (not windows). Returns mean delta and a 95% CI; the
    CI excluding zero is the pre-registered success signal."""
    holes = sorted(set(per_hole_a) & set(per_hole_b))
    deltas = np.array([per_hole_a[h] - per_hole_b[h] for h in holes
                       if np.isfinite(per_hole_a[h]) and np.isfinite(per_hole_b[h])])
    if len(deltas) < 2:
        return {"delta_mean": float("nan"), "ci_low": float("nan"),
                "ci_high": float("nan"), "n_holes": len(deltas),
                "excludes_zero": False}
    rng = np.random.default_rng(seed)
    boot = np.array([rng.choice(deltas, size=len(deltas), replace=True).mean()
                     for _ in range(n)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"delta_mean": float(deltas.mean()), "ci_low": float(lo),
            "ci_high": float(hi), "n_holes": len(deltas),
            "excludes_zero": bool(lo > 0 or hi < 0)}


# --------------------------------------------------------------------------- #
# Pre-registration guard (T3.4 / calibration finding F7)
# --------------------------------------------------------------------------- #

# The pre-registered boundary tolerance, frozen in commit 96c0454 before any
# results existed. Changing the SCORED tolerance away from this without a
# documented override is a post-hoc change (checklist item B).
PREREGISTERED_DEPTH_TOLERANCE_M = 2.0


def preregistered_tolerance_ok(scored_tol: float, *,
                               override_reason: str | None = None) -> dict:
    """Guard that the scored boundary tolerance matches the pre-registered value.

    Returns {ok, scored, preregistered, override_reason}. ok is True iff the
    scored tolerance equals the pre-registered value OR a non-empty
    override_reason is supplied (which must also be documented in the README).
    """
    matches = abs(float(scored_tol) - PREREGISTERED_DEPTH_TOLERANCE_M) < 1e-9
    ok = matches or bool(override_reason)
    return {"ok": ok, "scored": float(scored_tol),
            "preregistered": PREREGISTERED_DEPTH_TOLERANCE_M,
            "override_reason": override_reason}
