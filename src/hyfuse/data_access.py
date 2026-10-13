"""data_access.py (T3.3): load composited features + logged geology + assays
for the shortlisted holes, from cached data only (no NVCL fetch here).

Centralises: the hole -> WAMEX CollarId map (parsed from config/holes.yaml
comments), the DASC DuckDB attach, and per-hole loaders used by the ablation.
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import pandas as pd
import yaml

from hyfuse import qc
from hyfuse.composite import composite_minerals, make_windows, overlap_weight_assays

ROOT = Path(__file__).resolve().parent.parent.parent
DERIVED_HOLES = ROOT / "data" / "derived" / "holes"
DASC_SQLITE = ROOT / "data" / "raw" / "dasc" / "HyLogger_Dataset_Package.sqlite"
HOLES_YAML = ROOT / "config" / "holes.yaml"
PARAMS = ROOT / "config" / "params.yaml"


def load_params() -> dict:
    return yaml.safe_load(PARAMS.read_text())


def hole_collar_map() -> dict[str, int]:
    """Parse 'hole  # CollarId NNN' comments from config/holes.yaml."""
    out: dict[str, int] = {}
    for line in HOLES_YAML.read_text().splitlines():
        m = re.match(r"\s*-\s*(\S+)\s*#.*CollarId\s+(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def _dasc() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL sqlite; LOAD sqlite;")
    con.execute(f"ATTACH '{DASC_SQLITE}' AS dasc (TYPE sqlite, READ_ONLY);")
    return con


def load_tidy(hole_id: str) -> pd.DataFrame:
    df = pd.read_parquet(DERIVED_HOLES / f"{hole_id}.parquet")
    df["hole_id"] = hole_id
    return df


def composited_views(hole_id: str, win: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-view mineral-group composition matrices (swir, tir) for a hole.

    Windows anchored at the collar (origin 0) so features and assays share one
    grid and their window indices align.
    """
    from hyfuse.features import composition_matrix
    comp = composite_minerals(load_tidy(hole_id), win=win, origin=0.0)
    return composition_matrix(comp, "swir"), composition_matrix(comp, "tir")


def logged_geology(collar_id: int) -> pd.DataFrame:
    con = _dasc()
    return con.execute(
        "SELECT FromDepth AS depth_from, ToDepth AS depth_to "
        "FROM dasc.wamex_dh_geology WHERE CollarId = ? AND FromDepth IS NOT NULL "
        "ORDER BY FromDepth", [collar_id]).fetchdf()


def assays_long(hole_id: str, collar_id: int, targets: list[str],
                plausibility: dict) -> pd.DataFrame:
    """Hygiene-cleaned long assays for the target elements of one hole."""
    con = _dasc()
    cols = ", ".join(["FromDepth AS depth_from", "ToDepth AS depth_to", *targets])
    wide = con.execute(
        f"SELECT {cols} FROM dasc.wamex_assay_flat_data "
        "WHERE CollarId = ? AND FromDepth IS NOT NULL", [collar_id]).fetchdf()
    if wide.empty:
        return wide
    return qc.assays_wide_to_long(wide, hole_id, elements=targets,
                                  plausibility_ppm=plausibility)


def windowed_assays(hole_id: str, collar_id: int, win: float,
                    targets: list[str], plausibility: dict) -> pd.DataFrame:
    """Overlap-weighted assay target(s) per 5 m window for a hole."""
    long = assays_long(hole_id, collar_id, targets, plausibility)
    if long.empty:
        return long
    d1 = float(long["depth_to"].max())
    win_df = make_windows(0.0, d1, win, hole_id)  # collar origin, shared grid
    return overlap_weight_assays(win_df, long)
