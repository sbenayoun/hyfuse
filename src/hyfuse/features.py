"""features.py (T1.6, T1.7): tidy depth-aligned Parquet + coverage audit.

T1.6: for each hole in config/holes.yaml, read the TSG package, build the tidy
long table (read.py), and write one Parquet per hole to data/derived/holes/.
Final Mask is recorded as a column (not pre-filtered) so downstream QC and the
corruption tests can exercise masking explicitly; qc.apply_final_mask does the
keep==1 filtering where needed.

T1.7 coverage audit is a separate entry point (coverage.py / make features).
Compositional CLR features (T2.3) are added later.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from hyfuse import qc, read

log = logging.getLogger("hyfuse.features")

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_HOLES = ROOT / "data" / "raw" / "holes"
DERIVED_HOLES = ROOT / "data" / "derived" / "holes"
HOLES_YAML = ROOT / "config" / "holes.yaml"


# --------------------------------------------------------------------------- #
# T2.3 compositional (CLR) features — PER VIEW, never pooled across views.
# --------------------------------------------------------------------------- #

# Non-mineral group states excluded from the composition (kept elsewhere as
# explicit flags, but they are not real mineral parts of the rock).
_NON_COMPOSITION_GROUPS = {"", "INVALID", "NOTAROK"}


def composition_matrix(composited: pd.DataFrame, view: str) -> pd.DataFrame:
    """Per-window mineral-group abundance matrix for ONE view.

    Input: output of composite.composite_minerals (hole_id, win_from, win_to,
    view, mineral_group, mean_abundance, ...). Returns a frame indexed by
    (hole_id, win_from, win_to) with one column per real mineral group; absent
    groups are 0 (structural zero = not detectable in this view).
    """
    v = composited[composited["view"] == view].copy()
    v = v[~v["mineral_group"].isin(_NON_COMPOSITION_GROUPS)]
    v = v.dropna(subset=["mean_abundance"])
    if v.empty:
        return pd.DataFrame()
    mat = v.pivot_table(
        index=["hole_id", "win_from", "win_to"],
        columns="mineral_group",
        values="mean_abundance",
        fill_value=0.0,
    )
    mat.columns.name = None
    return mat


def multiplicative_replacement(mat: pd.DataFrame, delta: float) -> pd.DataFrame:
    """Replace zeros with delta and renormalise rows to sum 1 (simplex).

    Multiplicative (Martín-Fernández) style: zeros -> delta; non-zero parts are
    scaled by (1 - n_zero*delta) so each row still sums to 1. Rows that are all
    zero are left all-zero (handled/absent upstream).
    """
    arr = mat.to_numpy(dtype=float)
    out = arr.copy()
    for i in range(arr.shape[0]):
        row = arr[i]
        total = row.sum()
        if total <= 0:
            continue
        comp = row / total  # close to the simplex first
        zeros = comp == 0
        nz = ~zeros
        n_zero = int(zeros.sum())
        if n_zero == 0:
            out[i] = comp
            continue
        comp_new = comp.copy()
        comp_new[zeros] = delta
        comp_new[nz] = comp[nz] * (1.0 - n_zero * delta)
        out[i] = comp_new
    return pd.DataFrame(out, index=mat.index, columns=mat.columns)


def clr(mat: pd.DataFrame) -> pd.DataFrame:
    """Centered log-ratio of a strictly-positive composition matrix.

    clr(x)_j = ln(x_j) - mean_k ln(x_k). Requires all parts > 0 (apply
    multiplicative_replacement first). Returns same shape, columns suffixed
    '_clr'.
    """
    arr = mat.to_numpy(dtype=float)
    if (arr <= 0).any():
        raise ValueError("clr requires strictly positive parts; "
                         "apply multiplicative_replacement first")
    logx = np.log(arr)
    centred = logx - logx.mean(axis=1, keepdims=True)
    return pd.DataFrame(centred, index=mat.index,
                        columns=[f"{c}_clr" for c in mat.columns])


def hellinger(mat: pd.DataFrame) -> pd.DataFrame:
    """Hellinger (square-root) transform of a composition matrix.

    Closes each row to sum 1, then takes the element-wise square root. This is a
    standard compositional transform that:
      - handles structural zeros natively (no zero-replacement / delta needed),
      - is bounded and stable, and
      - (on the planted-truth test) PRESERVES domain-discriminative signal that
        CLR's geometric-mean centring destroys when many parts are near-zero.
    Columns suffixed '_hel'. Rows summing to 0 (aspectral) map to all-zero.
    """
    arr = mat.to_numpy(dtype=float)
    sums = arr.sum(axis=1, keepdims=True)
    comp = np.divide(arr, sums, out=np.zeros_like(arr), where=sums > 0)
    return pd.DataFrame(np.sqrt(comp), index=mat.index,
                        columns=[f"{c}_hel" for c in mat.columns])


def view_features(mat: pd.DataFrame, view: str, *, transform: str = "hellinger",
                  delta: float = 1e-6) -> pd.DataFrame:
    """Per-view compositional features (view-prefixed), transform-selectable.

    transform:
      - "hellinger" (default): sqrt of the closed composition. Robust to zeros;
        the project default after the planted-truth study (see reports).
      - "clr": centered log-ratio with multiplicative zero replacement (delta).
        Kept as an ablation; underperforms on planted truth.
    Drops all-zero (aspectral) windows. Columns prefixed with the view.
    """
    nz = mat[mat.sum(axis=1) > 0]
    if nz.empty:
        return nz
    if transform == "clr":
        out = clr(multiplicative_replacement(nz, delta))
    elif transform == "hellinger":
        out = hellinger(nz)
    else:
        raise ValueError(f"unknown transform: {transform}")
    out.columns = [f"{view}_{c}" for c in out.columns]
    return out


def clr_features(composited: pd.DataFrame, view: str,
                 delta: float = 1e-6,
                 min_nonzero_groups: int = 1) -> pd.DataFrame:
    """Full per-view CLR pipeline: matrix -> zero-replace -> CLR.

    Drops windows with fewer than `min_nonzero_groups` detectable groups.
    Returns the CLR feature matrix for the view (never mixes views). Columns are
    prefixed with the view ('swir_'/'tir_') so that when the fusion arm later
    concatenates both views, groups detectable in both (e.g. KAOLIN) stay
    distinct and do not collide.
    """
    mat = composition_matrix(composited, view)
    if mat.empty:
        return mat
    keep = (mat > 0).sum(axis=1) >= min_nonzero_groups
    mat = mat[keep]
    if mat.empty:
        return mat
    replaced = multiplicative_replacement(mat, delta)
    out = clr(replaced)
    out.columns = [f"{view}_{c}" for c in out.columns]
    return out


def build_hole(hole_id: str, instrument_gen: str = "infer") -> Path | None:
    """Read one fetched TSG hole -> tidy Parquet. Returns the Parquet path.

    instrument_gen defaults to 'infer' (derive HL generation from present views,
    R2 finding F2) so the column is a real confounder, not a constant 'unknown'.
    """
    folder = RAW_HOLES / hole_id
    if not folder.exists():
        log.error("hole folder missing (fetch first): %s", folder)
        return None
    df = read.read_hole(str(folder), hole_id=hole_id, instrument_gen=instrument_gen)
    if df.empty:
        log.error("no tidy rows produced for %s", hole_id)
        return None

    DERIVED_HOLES.mkdir(parents=True, exist_ok=True)
    out = DERIVED_HOLES / f"{hole_id}.parquet"
    df.to_parquet(out, index=False)

    summ = qc.mask_summary(df)
    metres = qc.metres_after_mask(df)
    log.info("%s: %d rows -> %s | mask=%s | kept_metres=%.1f",
             hole_id, len(df), out.name, summ, metres)
    return out


def _load_holes() -> list[str]:
    if not HOLES_YAML.exists():
        return []
    data = yaml.safe_load(HOLES_YAML.read_text()) or {}
    return list(data.get("holes") or [])


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        stream=sys.stdout)
    p = argparse.ArgumentParser(description="Build tidy per-hole Parquet (T1.6).")
    p.add_argument("holes", nargs="*", help="hole ids (default: config/holes.yaml)")
    args = p.parse_args(argv)

    holes = args.holes or _load_holes()
    if not holes:
        log.error("no holes given and config/holes.yaml is empty")
        return 2
    ok = 0
    for h in holes:
        if build_hole(h) is not None:
            ok += 1
    log.info("built %d/%d holes", ok, len(holes))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
