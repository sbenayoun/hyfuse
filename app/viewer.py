"""HyFuse interactive hole viewer (T2.8, T4.1).

Streamlit app: select a hole -> depth log with logged units, detected domains
and boundaries, mineral-group stacks. Later: SWIR/TIR stacks, per-arm domains,
assay overlay, ablation summary tab. Reads Parquet via DuckDB.

Run on WSL2:
    uv run streamlit run app/viewer.py --server.headless true
then open http://localhost:8501 in the Windows browser.
"""

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="HyFuse Viewer", layout="wide")
    st.title("HyFuse — HyLogger SWIR/TIR fusion viewer")
    st.info("Scaffold placeholder. Hole viewer is implemented in T2.8 / T4.1.")


if __name__ == "__main__":
    main()
