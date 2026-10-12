"""qc.py (T1.6, T2.2): data-quality rules for the tidy HyLogger table.

Rules (GSWA FAQ + reports/data_notes.md):
- Keep only Final Mask == 1 rows (clean core); drop mask==0.
- Keep 'invalid'/'aspectral' (and other non-mineral states) as EXPLICIT rows,
  not missing/zero. (They survive masking only if Final Mask == 1.)
- Use 'error' as the confidence measure (already null-sentinel-cleaned in read).
- Prefer Mineral Group over individual mineral for Level 1 (handled downstream;
  the tidy table keeps both columns).
- Wt1 == 1.0 is valid (single phase); never filtered.

Assay hygiene (T2.2) lives further down and is added when assays are wired in.
"""

from __future__ import annotations

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
