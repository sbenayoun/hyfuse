"""viewer_core.py (T2.8/T4.1): data + figure logic for the hole viewer.

Kept separate from app/viewer.py (the Streamlit shell) so the figure building is
importable and testable without launching Streamlit. Reads a per-hole tidy
Parquet, composites to windows, runs per-view domaining, and builds a Plotly
depth-log figure with mineral-group stacks, detected domain boundaries, and
(optionally) logged lithology interval boundaries.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import yaml

from hyfuse.composite import composite_minerals
from hyfuse.domains import domain_view
from hyfuse.evaluate import logged_boundaries
from hyfuse.features import clr_features

ROOT = Path(__file__).resolve().parent.parent.parent
DERIVED_HOLES = ROOT / "data" / "derived" / "holes"
PARAMS = ROOT / "config" / "params.yaml"
DASC_SQLITE = ROOT / "data" / "raw" / "dasc" / "HyLogger_Dataset_Package.sqlite"
REPORTS = ROOT / "reports"


def ablation_markdown() -> str:
    """Raw generated ablation report (reports/ablation.md), or a notice."""
    p = REPORTS / "ablation.md"
    if not p.exists():
        return ("_No `reports/ablation.md` yet — run `make evaluate` to generate "
                "the four-arm ablation._")
    return p.read_text()


def confounders_markdown() -> str:
    """Raw generated confounder report (reports/confounders.md), or a notice."""
    p = REPORTS / "confounders.md"
    if not p.exists():
        return "_No `reports/confounders.md` yet — run `make evaluate`._"
    return p.read_text()


def available_holes() -> list[str]:
    """Hole ids with a derived tidy Parquet on disk."""
    if not DERIVED_HOLES.exists():
        return []
    return sorted(p.stem for p in DERIVED_HOLES.glob("*.parquet"))


def load_params() -> dict:
    return yaml.safe_load(PARAMS.read_text()) if PARAMS.exists() else {}


def load_tidy(hole_id: str) -> pd.DataFrame:
    """Read a hole's tidy Parquet (via DuckDB) and ensure hole_id is set."""
    path = DERIVED_HOLES / f"{hole_id}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"no derived Parquet for {hole_id}: {path}")
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_parquet('{path}')").fetchdf()
    df["hole_id"] = hole_id
    return df


def load_logged_boundaries(collar_id: int | None) -> list[float]:
    """Interior logged lithology boundaries for a collar (empty if unavailable)."""
    if collar_id is None or not DASC_SQLITE.exists():
        return []
    con = duckdb.connect()
    con.execute("INSTALL sqlite; LOAD sqlite;")
    con.execute(f"ATTACH '{DASC_SQLITE}' AS dasc (TYPE sqlite, READ_ONLY);")
    g = con.execute(
        "SELECT FromDepth, ToDepth FROM dasc.wamex_dh_geology "
        "WHERE CollarId = ? AND FromDepth IS NOT NULL ORDER BY FromDepth",
        [collar_id],
    ).fetchdf()
    if g.empty:
        return []
    return logged_boundaries(g["FromDepth"].to_numpy(), g["ToDepth"].to_numpy())


def build_hole_view(hole_id: str, *, view: str = "swir",
                    logged: list[float] | None = None) -> dict:
    """Composite + domain one view of a hole; return data for plotting.

    Returns a dict with: windows (composited), features (CLR), domain result,
    and the logged boundary list. Safe on tiny holes (empty domains).
    """
    params = load_params()
    win = float(params.get("window_size_m", 5.0))
    delta = float(params.get("clr", {}).get("delta", 1e-6))
    seed = int(params.get("seed", 42))
    mi_m = float(params.get("min_interval_m", 1.0))
    min_iw = max(1, round(mi_m / win))

    tidy = load_tidy(hole_id)
    comp = composite_minerals(tidy, win=win)
    feats = clr_features(comp, view, delta=delta)
    result = None
    if not feats.empty:
        result = domain_view(feats, seed=seed, n_components=3,
                             min_cluster_size=3, min_interval_windows=min_iw,
                             seg_penalty=2.0)
    return {"hole_id": hole_id, "view": view, "composited": comp,
            "features": feats, "domains": result,
            "logged_boundaries": logged or []}


def make_figure(viewdata: dict) -> go.Figure:
    """Build a Plotly depth-log: mineral-group stacks + domain/logged boundaries.

    Depth increases DOWN the y-axis (reversed), as in a drill log.
    """
    comp = viewdata["composited"]
    view = viewdata["view"]
    fig = go.Figure()
    v = comp[comp["view"] == view].dropna(subset=["mean_abundance"]) if not comp.empty else comp

    if v is not None and not v.empty:
        depth = (v["win_from"] + v["win_to"]) / 2.0
        for grp, g in v.groupby("mineral_group"):
            d = (g["win_from"] + g["win_to"]) / 2.0
            fig.add_trace(go.Bar(
                y=d, x=g["mean_abundance"], name=str(grp),
                orientation="h", hovertemplate=f"{grp}: %{{x:.2f}} @ %{{y:.1f}} m",
            ))
        fig.update_layout(barmode="stack")
        _ = depth  # (depth span used implicitly by traces)

    # Detected domain boundaries (solid red lines).
    res = viewdata.get("domains")
    if res is not None:
        for b in res.boundaries:
            fig.add_hline(y=b, line_color="red", line_width=1,
                          annotation_text="domain", annotation_position="right")

    # Logged lithology boundaries (dashed grey lines).
    for b in viewdata.get("logged_boundaries", []):
        fig.add_hline(y=b, line_color="grey", line_dash="dash", line_width=1)

    fig.update_yaxes(autorange="reversed", title="Depth (m)")
    fig.update_xaxes(title="Mean abundance (per group)")
    fig.update_layout(
        title=f"{viewdata['hole_id']} — {view.upper()} mineral groups & domains",
        legend_title="Mineral group", height=800,
    )
    return fig


def export_hole(hole_id: str, out_dir: str, *, view: str = "tir",
                collar_id: int | None = None, as_png: bool = False) -> str:
    """Render one hole's depth-log figure to a standalone file for sharing.

    Default is a self-contained interactive HTML (opens in any browser, no server
    and no THREDDS/DASC access needed). PNG is optional and requires `kaleido`.
    Returns the written file path.
    """
    from pathlib import Path as _Path

    logged = load_logged_boundaries(collar_id) if collar_id else []
    data = build_hole_view(hole_id, view=view, logged=logged)
    fig = make_figure(data)
    out = _Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if as_png:
        path = out / f"{hole_id}_{view}.png"
        fig.write_image(str(path), width=1400, height=900, scale=2)
    else:
        path = out / f"{hole_id}_{view}.html"
        fig.write_html(str(path), include_plotlyjs="cdn")
    return str(path)


def make_side_by_side(hole_id: str, *, collar_id: int | None = None) -> go.Figure:
    """SWIR | TIR side-by-side depth logs for one hole (shared depth axis).

    Left = SWIR mineral-group stacks, right = TIR, each with its own detected
    domain boundaries (red) and the shared logged lithology boundaries (grey
    dashed). Depth increases downward. This is the "two views see different
    minerals" visual for the README / pitch slide 2.
    """
    from plotly.subplots import make_subplots

    logged = load_logged_boundaries(collar_id) if collar_id else []
    sw = build_hole_view(hole_id, view="swir", logged=logged)
    ti = build_hole_view(hole_id, view="tir", logged=logged)

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                        subplot_titles=("SWIR", "TIR"), horizontal_spacing=0.06)

    for col, data in ((1, sw), (2, ti)):
        comp = data["composited"]
        v = (comp[comp["view"] == data["view"]].dropna(subset=["mean_abundance"])
             if not comp.empty else comp)
        if v is not None and not v.empty:
            for grp, g in v.groupby("mineral_group"):
                d = (g["win_from"] + g["win_to"]) / 2.0
                fig.add_trace(
                    go.Bar(y=d, x=g["mean_abundance"], name=str(grp),
                           orientation="h", legendgroup=str(grp),
                           showlegend=(col == 1),
                           hovertemplate=f"{grp}: %{{x:.2f}} @ %{{y:.1f}} m"),
                    row=1, col=col)
        res = data.get("domains")
        if res is not None:
            for b in res.boundaries:
                fig.add_hline(y=b, line_color="red", line_width=1, row=1, col=col)
        for b in data.get("logged_boundaries", []):
            fig.add_hline(y=b, line_color="grey", line_dash="dash",
                          line_width=1, row=1, col=col)

    fig.update_layout(barmode="stack", height=900, width=1300,
                      title=f"{hole_id} — SWIR vs TIR (red = detected domains, "
                            "grey dashed = logged boundaries)",
                      legend_title="Mineral group")
    fig.update_yaxes(autorange="reversed", title="Depth (m)", row=1, col=1)
    fig.update_xaxes(title="mean abundance", row=1, col=1)
    fig.update_xaxes(title="mean abundance", row=1, col=2)
    return fig


def export_side_by_side(hole_id: str, out_dir: str, *,
                        collar_id: int | None = None,
                        as_png: bool = False) -> str:
    """Render the SWIR|TIR side-by-side figure to standalone HTML (or PNG)."""
    from pathlib import Path as _Path
    fig = make_side_by_side(hole_id, collar_id=collar_id)
    out = _Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if as_png:
        path = out / f"{hole_id}_swir_tir.png"
        fig.write_image(str(path), width=1300, height=900, scale=2)
    else:
        path = out / f"{hole_id}_swir_tir.html"
        fig.write_html(str(path), include_plotlyjs="cdn")
    return str(path)
