"""read.py (T1.3, T1.6): read a TSG hole into a tidy depth-aligned table.

Produces, per hole, a long DataFrame with one row per measurement sample x view:
    hole_id, depth_from, depth_to, view (swir|tir),
    mineral_group, mineral, abundance, error, final_mask,
    processing_level, instrument_gen

Design decisions (evidenced in reports/data_notes.md):
- SWIR mineral results live in the pytsg `.nir` Spectra (380-2500 nm covers
  VNIR+SWIR); TIR in `.tir`.
- Mineral results are TSG scalar columns named `Min1 <suf>`, `Grp1 <suf>`,
  `Wt1 <suf>`, `Error <suf>`. The <suf> (processing level) varies per hole/view
  (e.g. sTSAS/uTSAS for SWIR; sjCLST/ujCLST for TIR). We DISCOVER it, prefer the
  system-constrained variant, and IGNORE the vis TSAV results (sTSAV/uTSAV).
- `Final Mask` is a binary scalar: 1.0 = keep (clean core), 0.0 = drop. On real
  NVCL holes it exists in both views; on the CSIRO example it is absent (treated
  as all-keep with a recorded warning).
- Numeric scalars carry the float32 null sentinel ~ -3.4e38 on masked rows; we
  null anything with |x| >= SENTINEL_ABS before use.
- Depth is sampleheaders['D'] (metres). We emit depth_from/depth_to by midpoint
  spacing (point samples -> half-step intervals).

ASSUMPTION: point-sample depth 'D' is the sample centre; depth_from/to are built
from half the local spacing. VERIFY against tray geometry if needed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

log = logging.getLogger("hyfuse.read")

# TSG float null sentinel is ~ -3.4028e38 (float32 min). Treat large magnitudes
# as null; valid Wt1 in [0,1], Error modest positive.
SENTINEL_ABS = 1e30

# Non-mineral class states that must stay explicit (not coerced to missing/zero).
EXPLICIT_STATES = {
    "aspectral", "notinlibrary", "dark", "noisy", "higherror", "maskedoff",
    "invalid", "notarok",
}

# Processing-suffix preference: system-constrained first, then unconstrained.
# IGNORE the vis TSAV family (TSAV) entirely per GSWA data-quality rules.
_IGNORE_SUFFIX_TOKENS = ("tsav",)
_PREFER_ORDER = ("stsas", "sjclst", "stsat", "utsas", "ujclst", "utsat")


@dataclass
class ViewColumns:
    """Resolved scalar column names for one view's top mineral result."""

    suffix: str
    mineral: str  # Min1 <suf>
    group: str    # Grp1 <suf>
    weight: str   # Wt1 <suf>
    error: str    # Error <suf>


def _discover_suffix(columns: list[str]) -> str | None:
    """Find the best processing suffix with a full Min1/Grp1/Wt1 set."""
    suffixes: set[str] = set()
    for c in columns:
        for prefix in ("Min1 ", "Grp1 ", "Wt1 "):
            if c.startswith(prefix):
                suffixes.add(c[len(prefix):])
    # Require a complete Min1+Grp1+Wt1 set and drop the ignored TSAV family.
    complete = []
    for suf in suffixes:
        has = all(f"{p}{suf}" in columns for p in ("Min1 ", "Grp1 ", "Wt1 "))
        if has and not any(tok in suf.lower() for tok in _IGNORE_SUFFIX_TOKENS):
            complete.append(suf)
    if not complete:
        return None
    # Prefer by the known order, else first alphabetically for determinism.
    complete.sort(key=lambda s: (_PREFER_ORDER.index(s.lower())
                                 if s.lower() in _PREFER_ORDER else 99, s))
    return complete[0]


def _resolve_columns(columns: list[str]) -> ViewColumns | None:
    suf = _discover_suffix(columns)
    if suf is None:
        return None
    err = f"Error {suf}" if f"Error {suf}" in columns else ""
    return ViewColumns(
        suffix=suf,
        mineral=f"Min1 {suf}",
        group=f"Grp1 {suf}",
        weight=f"Wt1 {suf}",
        error=err,
    )


def _null_sentinel(series: pd.Series) -> pd.Series:
    """Replace the TSG float null sentinel (large magnitude) with NaN."""
    s = pd.to_numeric(series, errors="coerce")
    return s.mask(s.abs() >= SENTINEL_ABS)


def _depths_from_points(d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build depth_from/depth_to from point-sample centres via half-spacing."""
    d = np.asarray(d, dtype=float)
    n = d.size
    if n == 0:
        return d, d
    if n == 1:
        return d - 0.005, d + 0.005
    mid = (d[:-1] + d[1:]) / 2.0
    frm = np.empty(n)
    to = np.empty(n)
    frm[0] = d[0] - (mid[0] - d[0])
    frm[1:] = mid
    to[:-1] = mid
    to[-1] = d[-1] + (d[-1] - mid[-1])
    return frm, to


def _tidy_view(spectra, view: str, hole_id: str, processing_hint: str) -> pd.DataFrame:
    sc = spectra.scalars
    cols = list(sc.columns)
    resolved = _resolve_columns(cols)
    if resolved is None:
        log.warning("%s/%s: no Min1/Grp1/Wt1 scalar set found; skipping view",
                    hole_id, view)
        return pd.DataFrame()

    depth = spectra.sampleheaders["D"].to_numpy(dtype=float)
    frm, to = _depths_from_points(depth)

    mineral = sc[resolved.mineral].astype("string").str.strip()
    group = sc[resolved.group].astype("string").str.strip()
    abundance = _null_sentinel(sc[resolved.weight])
    error = _null_sentinel(sc[resolved.error]) if resolved.error else np.nan

    if "Final Mask" in cols:
        final_mask = _null_sentinel(sc["Final Mask"]).fillna(0).astype(int)
    else:
        log.warning("%s/%s: no 'Final Mask' column; treating all rows as keep",
                    hole_id, view)
        final_mask = pd.Series(1, index=sc.index, dtype=int)

    df = pd.DataFrame({
        "hole_id": hole_id,
        "depth_from": frm,
        "depth_to": to,
        "view": view,
        "mineral_group": group,
        "mineral": mineral,
        "abundance": abundance.to_numpy(),
        "error": error.to_numpy() if hasattr(error, "to_numpy") else error,
        "final_mask": final_mask.to_numpy(),
        "processing_level": resolved.suffix,
        "instrument_gen": processing_hint,
    })
    # Mark explicit non-mineral states (kept, not dropped).
    df["is_explicit_state"] = (
        df["mineral"].str.lower().isin(EXPLICIT_STATES)
        | df["mineral_group"].str.lower().isin(EXPLICIT_STATES)
    )
    return df


def read_hole(folder: str, hole_id: str | None = None,
              instrument_gen: str = "unknown") -> pd.DataFrame:
    """Read one TSG package folder into the tidy long table (SWIR+TIR).

    If instrument_gen == 'infer', derive it from which spectral views are
    present (per the GSWA 'Spectral Regions' slide): MIR present -> HyLogger 4;
    TIR present (no MIR) -> HyLogger 3+; VNIR/SWIR only -> HyLogger 2+. This
    makes instrument_gen a real confounder column instead of a constant.
    """
    import pytsg

    hid = hole_id or _infer_hole_id(folder)
    data = pytsg.read_tsg(folder)
    gen = instrument_gen
    if instrument_gen == "infer":
        gen = infer_instrument_gen(data)
    frames = []
    if data.nir is not None:
        frames.append(_tidy_view(data.nir, "swir", hid, gen))
    if data.tir is not None:
        frames.append(_tidy_view(data.tir, "tir", hid, gen))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def infer_instrument_gen(data) -> str:
    """Infer HyLogger generation from present spectral views.

    MIR (2500-5500 nm) -> HyLogger 4; TIR (5500-15000 nm) -> HyLogger 3+;
    VNIR-SWIR only -> HyLogger 2+. VERIFY against the package metadata where a
    firmer instrument field is available.
    """
    if getattr(data, "mir", None) is not None:
        return "HL4"
    if getattr(data, "tir", None) is not None:
        return "HL3+"
    return "HL2+"


def _infer_hole_id(folder: str) -> str:
    from pathlib import Path
    return Path(folder).name
