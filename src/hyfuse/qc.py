"""qc.py (T1.6, T2.2): data-quality rules for the tidy HyLogger table + assays.

Rules (GSWA FAQ + reports/data_notes.md):
- Keep only Final Mask == 1 rows (clean core); drop mask==0.
- Keep 'invalid'/'aspectral' (and other non-mineral states) as EXPLICIT rows,
  not missing/zero. (They survive masking only if Final Mask == 1.)
- Use 'error' as the confidence measure (already null-sentinel-cleaned in read).
- Prefer Mineral Group over individual mineral for Level 1 (handled downstream;
  the tidy table keeps both columns).
- Wt1 == 1.0 is valid (single phase); never filtered.

Assay hygiene (T2.2):
- Below-detection is encoded as NEGATIVE values (R1 reviewer F3, confirmed on
  real data): x < 0 means "below |x|". Impute censored value = |x| / 2 and keep
  a 'below_detection' flag column. ASSUMPTION (|x|/2); ablatable.
- Plausibility ranges per element (params.assay_hygiene.plausibility_ppm): values
  outside are FLAGGED ('implausible'), never silently dropped.
- Melt the wide DASC assay table to long form for overlap_weight_assays:
  hole_id, depth_from, depth_to, element, value (+ below_detection, implausible).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def apply_final_mask(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only Final Mask == 1 rows. Returns a copy.

    Direction evidenced on ETG0187: 1.0 = keep (clean core), 0.0 = drop.
    """
    if "final_mask" not in df.columns:
        return df.copy()
    kept = df[df["final_mask"] == 1].copy()
    return kept.reset_index(drop=True)


def mask_summary(df: pd.DataFrame) -> dict[str, int]:
    """Counts of kept/dropped rows per view, for the coverage report."""
    out: dict[str, int] = {}
    if "final_mask" not in df.columns:
        return out
    for view, g in df.groupby("view"):
        out[f"{view}_total"] = len(g)
        out[f"{view}_kept"] = int((g["final_mask"] == 1).sum())
        out[f"{view}_dropped"] = int((g["final_mask"] == 0).sum())
    return out


def metres_after_mask(df: pd.DataFrame) -> float:
    """Total downhole metres covered by kept rows (sum of interval lengths)."""
    kept = apply_final_mask(df)
    if kept.empty:
        return 0.0
    length = (kept["depth_to"] - kept["depth_from"]).clip(lower=0)
    return float(length.sum())


# --------------------------------------------------------------------------- #
# Assay hygiene (T2.2)
# --------------------------------------------------------------------------- #

def resolve_below_detection(value: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Resolve negative (below-detection) assay values.

    Convention (confirmed on real DASC data): x < 0 means "below |x|" (the
    detection limit). Returns (resolved_value, below_detection_flag) where the
    resolved value imputes |x| / 2 for censored rows. ASSUMPTION: |x|/2.
    """
    v = pd.to_numeric(value, errors="coerce")
    below = v < 0
    resolved = v.where(~below, v.abs() / 2.0)
    return resolved, below.fillna(False)


def flag_implausible(value: pd.Series, element: str,
                     ranges: dict[str, list[float]] | None) -> pd.Series:
    """Boolean flag: value outside the element's plausibility range.

    ranges: {element: [lo, hi]} from params.assay_hygiene.plausibility_ppm.
    Rows with no range for the element are never flagged. NaN -> not flagged.
    """
    v = pd.to_numeric(value, errors="coerce")
    if not ranges or element not in ranges:
        return pd.Series(False, index=v.index)
    lo, hi = ranges[element]
    return ((v < lo) | (v > hi)).fillna(False)


def assays_wide_to_long(
    wide: pd.DataFrame,
    hole_id: str,
    *,
    elements: list[str] | None = None,
    plausibility_ppm: dict[str, list[float]] | None = None,
) -> pd.DataFrame:
    """Melt a wide DASC assay frame to the long form the compositor expects.

    wide: columns depth_from, depth_to (+ MidDepth optional) and element columns
          like 'Au_PPM', 'Cu_PPM', ... (DASC naming, units in the suffix).
    Returns long rows: hole_id, depth_from, depth_to, element, value,
    below_detection, implausible. Below-detection resolved; implausible flagged
    (not dropped). Null values dropped (no measurement).
    """
    out_cols = ["hole_id", "depth_from", "depth_to", "element", "value",
                "below_detection", "implausible"]
    id_cols = [c for c in ("depth_from", "depth_to") if c in wide.columns]
    if not id_cols:
        raise ValueError("wide assay frame needs depth_from/depth_to columns")

    element_cols = elements or [
        c for c in wide.columns
        if c.endswith(("_PPM", "_PCT", "_PPB")) and c not in id_cols
    ]
    if not element_cols:
        return pd.DataFrame(columns=out_cols)

    frames = []
    for el in element_cols:
        if el not in wide.columns:
            continue
        raw = pd.to_numeric(wide[el], errors="coerce")
        resolved, below = resolve_below_detection(raw)
        implausible = flag_implausible(resolved, el, plausibility_ppm)
        part = pd.DataFrame({
            "hole_id": hole_id,
            "depth_from": wide["depth_from"].to_numpy(),
            "depth_to": wide["depth_to"].to_numpy(),
            "element": el,
            "value": resolved.to_numpy(),
            "below_detection": below.to_numpy(),
            "implausible": implausible.to_numpy(),
        })
        part = part[~np.isnan(part["value"])]
        frames.append(part)

    if not frames:
        return pd.DataFrame(columns=out_cols)
    return pd.concat(frames, ignore_index=True)[out_cols]


# --------------------------------------------------------------------------- #
# Corruption guards (T2.7) — explicit detectors the corruption tests assert on.
# --------------------------------------------------------------------------- #

def assay_unit_sanity(long_assays: pd.DataFrame,
                      plausibility_ppm: dict[str, list[float]] | None) -> dict:
    """Summarise implausible assay fractions per element (catches x1000 errors).

    Returns {element: {n, n_implausible, frac_implausible}}. A unit error that
    multiplies values by 1000 pushes most rows past the plausibility cap, so
    frac_implausible jumps from ~0 to ~1 — the signal the x1000 test asserts.
    """
    out: dict[str, dict] = {}
    if long_assays.empty:
        return out
    for el, g in long_assays.groupby("element"):
        flagged = flag_implausible(g["value"], el, plausibility_ppm)
        n = len(g)
        ni = int(flagged.sum())
        out[el] = {"n": n, "n_implausible": ni,
                   "frac_implausible": (ni / n) if n else 0.0}
    return out


def hole_id_consistency(abundance: pd.DataFrame, other: pd.DataFrame,
                        *, key: str = "hole_id") -> dict:
    """Check that hole ids line up between two tables before an interval join.

    Returns overlap stats; if the id sets are disjoint (e.g. ids were shuffled
    between abundance and logs), overlap == 0 and `consistent` is False — the
    signal the shuffled-id test asserts.
    """
    a = set(map(str, abundance[key].unique()))
    b = set(map(str, other[key].unique()))
    inter = a & b
    return {"n_abundance_ids": len(a), "n_other_ids": len(b),
            "n_overlap": len(inter),
            "consistent": len(inter) > 0,
            "overlap_fraction": (len(inter) / max(1, len(a | b)))}


def inter_hole_outlier_holes(long_assays: pd.DataFrame, element: str,
                             *, factor: float = 50.0) -> list[str]:
    """Flag holes whose median assay is wildly out of line with the others.

    Catches a modest per-hole scaling error (e.g. one hole x1000) that stays
    UNDER the absolute plausibility cap and so is not caught by flag_implausible.
    A hole is flagged if its median target value is > `factor` x the global
    median of all OTHER holes' medians (robust to one bad hole). Returns the
    flagged hole_ids. (R2/calibration finding F7.)
    """
    g = long_assays[long_assays["element"] == element]
    if g.empty or "hole_id" not in g.columns:
        return []
    med = g.groupby("hole_id")["value"].median()
    if len(med) < 3:
        return []
    flagged = []
    for hole, m in med.items():
        others = med.drop(hole)
        ref = others.median()
        if ref > 0 and m > factor * ref:
            flagged.append(str(hole))
    return flagged
