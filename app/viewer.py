"""HyFuse interactive hole viewer (T2.8, extended in T4.1).

Thin Streamlit shell over src/hyfuse/viewer_core.py. Select a hole and a view
(SWIR/TIR); see a depth log of mineral-group stacks with detected domain
boundaries and (where available) logged lithology boundaries.

Run on WSL2:
    uv run streamlit run app/viewer.py --server.headless true
then open http://localhost:8501 in the Windows browser.
"""

import streamlit as st

from hyfuse import viewer_core


def main() -> None:
    st.set_page_config(page_title="HyFuse Viewer", layout="wide")
    st.title("HyFuse — HyLogger SWIR/TIR fusion viewer")

    holes = viewer_core.available_holes()
    if not holes:
        st.warning(
            "No derived per-hole Parquet found in data/derived/holes/. "
            "Run `make fetch` then `make features` first."
        )
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        hole = st.selectbox("Hole", holes)
    with col2:
        view = st.radio("View", ["swir", "tir"], horizontal=True)
    with col3:
        collar = st.text_input("WAMEX CollarId (optional, for logged boundaries)")

    logged = []
    if collar.strip().isdigit():
        logged = viewer_core.load_logged_boundaries(int(collar.strip()))

    data = viewer_core.build_hole_view(hole, view=view, logged=logged)
    res = data["domains"]
    n_dom = res.windows["domain"].nunique() if res is not None else 0
    n_bnd = len(res.boundaries) if res is not None else 0
    st.caption(f"{hole} · {view.upper()} · {n_dom} domains · {n_bnd} detected "
               f"boundaries · {len(logged)} logged boundaries")

    st.plotly_chart(viewer_core.make_figure(data), use_container_width=True)

    with st.expander("Composited windows (data behind the plot)"):
        st.dataframe(data["composited"])


if __name__ == "__main__":
    main()
