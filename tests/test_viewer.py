"""T2.8 tests: viewer_core figure building (no Streamlit needed)."""

import pandas as pd
import plotly.graph_objects as go

from hyfuse import viewer_core


def _viewdata_with_data():
    comp = pd.DataFrame({
        "hole_id": ["H"] * 4,
        "win_from": [0.0, 0.0, 5.0, 5.0],
        "win_to": [5.0, 5.0, 10.0, 10.0],
        "view": ["swir", "swir", "swir", "swir"],
        "mineral_group": ["KAOLIN", "WHITE-MICA", "KAOLIN", "SILICA"],
        "mean_abundance": [0.6, 0.4, 0.7, 0.3],
    })
    return {
        "hole_id": "H", "view": "swir", "composited": comp,
        "features": pd.DataFrame(), "domains": None,
        "logged_boundaries": [7.0],
    }


def test_make_figure_builds_stacked_bars_and_logged_line():
    fig = viewer_core.make_figure(_viewdata_with_data())
    assert isinstance(fig, go.Figure)
    # one horizontal bar trace per mineral group present (KAOLIN, WHITE-MICA, SILICA)
    bar_names = {t.name for t in fig.data if isinstance(t, go.Bar)}
    assert {"KAOLIN", "WHITE-MICA", "SILICA"} <= bar_names
    assert fig.layout.barmode == "stack"
    # depth axis reversed (down-hole)
    assert fig.layout.yaxis.autorange == "reversed"
    # a logged boundary line was added as a shape (hline)
    assert len(fig.layout.shapes) >= 1


def test_make_figure_empty_is_safe():
    empty = {"hole_id": "H", "view": "swir",
             "composited": pd.DataFrame(), "features": pd.DataFrame(),
             "domains": None, "logged_boundaries": []}
    fig = viewer_core.make_figure(empty)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0  # no traces, but no crash


def test_build_hole_view_on_real_etg0187_if_present():
    # Integration smoke test: only runs if the derived Parquet exists.
    holes = viewer_core.available_holes()
    if "ETG0187" not in holes:
        return
    data = viewer_core.build_hole_view("ETG0187", view="swir")
    assert data["hole_id"] == "ETG0187"
    assert not data["composited"].empty
    fig = viewer_core.make_figure(data)
    assert isinstance(fig, go.Figure)
