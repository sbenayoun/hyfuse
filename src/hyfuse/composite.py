"""composite.py (T2.1): depth-window compositing + overlap-weighted joins.

Uses DuckDB for the interval-overlap arithmetic (its strength) and returns tidy
pandas frames for downstream feature building. Three pieces, each separately
testable:

1. make_windows(d0, d1, win) -> fixed [win_from, win_to) windows over a range.
2. composite_minerals(tidy, win) -> mean mineral-group abundance per window/view
   over mask-on rows (sample midpoint decides window membership).
3. overlap_weight_assays(windows, assays_long) -> per window/element, the mean
   assay value weighted by the length each interval overlaps the window.

Overlap-weighting rule (plan T2.1): overlap = max(0, min(win_to,a_to) -
max(win_from,a_from)); value_wmean = sum(value*overlap)/sum(overlap). Never
average blindly across overlapping intervals.

Assay values are expected to be below-detection-resolved upstream (qc, T2.2);
this module does the geometry only.
"""

from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd


def make_windows(d0: float, d1: float, win: float, hole_id: str = "") -> pd.DataFrame:
    """Fixed [win_from, win_to) windows covering [d0, d1); last clipped to d1."""
    if win <= 0:
        raise ValueError("win must be > 0")
    if d1 <= d0:
        return pd.DataFrame(columns=["hole_id", "win_from", "win_to"])
    n = int(np.ceil((d1 - d0) / win))
    starts = d0 + np.arange(n) * win
    ends = np.minimum(starts + win, d1)
    return pd.DataFrame({"hole_id": hole_id, "win_from": starts, "win_to": ends})


def composite_minerals(tidy: pd.DataFrame, win: float) -> pd.DataFrame:
    """Mean mineral-group abundance per (window, view) over mask-on rows.

    Membership: a sample belongs to the window containing its depth midpoint.
    Returns columns: hole_id, win_from, win_to, view, mineral_group,
    mean_abundance, n_samples.
    """
    masked = tidy[tidy["final_mask"] == 1].copy()
    if masked.empty:
        return pd.DataFrame(columns=[
            "hole_id", "win_from", "win_to", "view", "mineral_group",
            "mean_abundance", "n_samples",
        ])
    hole_id = str(masked["hole_id"].iloc[0])
    d0 = float(masked["depth_from"].min())
    d1 = float(masked["depth_to"].max())
    windows = make_windows(d0, d1, win, hole_id)

    con = duckdb.connect()
    con.register("tidy", masked)
    con.register("win", windows)
    q = """
    WITH t AS (
        SELECT *, (depth_from + depth_to)/2.0 AS mid FROM tidy
    )
    SELECT w.hole_id, w.win_from, w.win_to, t.view, t.mineral_group,
           avg(t.abundance) AS mean_abundance,
           count(*)         AS n_samples
    FROM win w
    JOIN t ON t.mid >= w.win_from AND t.mid < w.win_to
    GROUP BY w.hole_id, w.win_from, w.win_to, t.view, t.mineral_group
    ORDER BY w.win_from, t.view, t.mineral_group
    """
    return con.execute(q).fetchdf()


def overlap_weight_assays(windows: pd.DataFrame,
                          assays_long: pd.DataFrame) -> pd.DataFrame:
    """Overlap-length-weighted assay mean per (window, element).

    windows: hole_id, win_from, win_to.
    assays_long: hole_id, depth_from, depth_to, element, value.
    Returns: hole_id, win_from, win_to, element, value_wmean, total_overlap.
    """
    cols = ["hole_id", "win_from", "win_to", "element", "value_wmean",
            "total_overlap"]
    if windows.empty or assays_long.empty:
        return pd.DataFrame(columns=cols)

    con = duckdb.connect()
    con.register("win", windows)
    con.register("assays", assays_long)
    q = """
    WITH ov AS (
        SELECT w.hole_id, w.win_from, w.win_to, a.element, a.value,
               greatest(0.0,
                 least(w.win_to, a.depth_to) - greatest(w.win_from, a.depth_from)
               ) AS overlap_len
        FROM win w
        JOIN assays a
          ON a.hole_id = w.hole_id
         AND a.depth_from < w.win_to
         AND a.depth_to   > w.win_from
    )
    SELECT hole_id, win_from, win_to, element,
           sum(value * overlap_len) / nullif(sum(overlap_len), 0) AS value_wmean,
           sum(overlap_len) AS total_overlap
    FROM ov
    WHERE overlap_len > 0
    GROUP BY hole_id, win_from, win_to, element
    ORDER BY win_from, element
    """
    return con.execute(q).fetchdf()
