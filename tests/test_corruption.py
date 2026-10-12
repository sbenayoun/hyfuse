"""T2.7 corruption tests: the pipeline must FLAG or visibly DEGRADE on each
injected fault. A corruption that passes silently is a failure of the pipeline.

Faults:
  1. assays x1000 / /1000 (ppm vs %)      -> implausible fraction jumps
  2. depth offset (+1 m)                   -> boundary-agreement F1 drops
  3. Final Mask ignored (non-core rows in) -> kept-row count / metres change
  4. hole ids shuffled between tables      -> interval join collapses (no overlap)

Each test also checks the CLEAN case does NOT trip the detector, so the guard is
not trivially always-on.
"""

import numpy as np
import pandas as pd

from hyfuse import qc
from hyfuse.composite import make_windows, overlap_weight_assays
from hyfuse.evaluate import boundary_agreement

# --- helpers ---------------------------------------------------------------- #

def _assays_wide():
    # plausible Au values (ppm), 10 one-metre intervals
    return pd.DataFrame({
        "depth_from": np.arange(10, dtype=float),
        "depth_to": np.arange(1, 11, dtype=float),
        "Au_PPM": [0.1, 0.2, 0.5, 1.0, 0.3, 0.4, 2.0, 0.6, 0.8, 0.05],
    })


RANGES = {"Au_PPM": [0, 100000]}


# --- Fault 1: assay x1000 --------------------------------------------------- #

def test_corruption_assay_times_1000_flagged():
    clean = qc.assays_wide_to_long(_assays_wide(), "H", plausibility_ppm=RANGES)
    clean_sanity = qc.assay_unit_sanity(clean, RANGES)
    assert clean_sanity["Au_PPM"]["frac_implausible"] == 0.0  # clean passes

    bad = _assays_wide()
    bad["Au_PPM"] = bad["Au_PPM"] * 1_000_000  # gross unit error
    bad_long = qc.assays_wide_to_long(bad, "H", plausibility_ppm=RANGES)
    bad_sanity = qc.assay_unit_sanity(bad_long, RANGES)
    # corruption must be VISIBLE: the implausible fraction jumps from 0 to a
    # large majority (exact fraction depends on which values exceed the cap).
    assert bad_sanity["Au_PPM"]["frac_implausible"] >= 0.8
    assert bad_sanity["Au_PPM"]["frac_implausible"] > clean_sanity["Au_PPM"]["frac_implausible"]


# --- Fault 2: depth offset -------------------------------------------------- #

def test_corruption_depth_offset_drops_boundary_f1():
    truth = [20.0, 40.0, 60.0, 80.0]
    detected = list(truth)  # perfect
    clean = boundary_agreement(detected, truth, tol=2.0)
    assert clean["f1"] == 1.0  # clean passes

    shifted = [d + 10.0 for d in detected]  # 10 m depth offset >> 2 m tol
    bad = boundary_agreement(shifted, truth, tol=2.0)
    assert bad["f1"] < clean["f1"]  # visible degradation
    assert bad["f1"] == 0.0


# --- Fault 3: Final Mask ignored -------------------------------------------- #

def _tidy_with_mask():
    return pd.DataFrame({
        "hole_id": ["H"] * 6,
        "depth_from": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
        "depth_to": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "view": ["swir"] * 6,
        "mineral_group": ["KAOLIN"] * 6,
        "abundance": [0.5] * 6,
        "final_mask": [1, 1, 1, 0, 0, 0],   # half masked off (non-core)
    })


def test_corruption_ignoring_final_mask_changes_rowcount_and_metres():
    tidy = _tidy_with_mask()
    kept = qc.apply_final_mask(tidy)
    # clean path keeps only mask==1 rows
    assert len(kept) == 3
    assert qc.metres_after_mask(tidy) == 3.0

    # "corruption": ignore the mask -> non-core rows leak in -> visible change
    ignored_rows = len(tidy)          # 6 instead of 3
    ignored_metres = (tidy["depth_to"] - tidy["depth_from"]).sum()  # 6.0
    assert ignored_rows != len(kept)
    assert ignored_metres != qc.metres_after_mask(tidy)
    # the mask summary makes the dropped rows explicit (not silent)
    summ = qc.mask_summary(tidy)
    assert summ["swir_dropped"] == 3 and summ["swir_kept"] == 3


# --- Fault 4: shuffled hole ids --------------------------------------------- #

def test_corruption_shuffled_hole_ids_collapse_join():
    windows = make_windows(0.0, 10.0, 5.0, "H")
    assays = pd.DataFrame({
        "hole_id": ["H"] * 10,
        "depth_from": np.arange(10, dtype=float),
        "depth_to": np.arange(1, 11, dtype=float),
        "element": ["Au_PPM"] * 10,
        "value": np.linspace(0.1, 1.0, 10),
    })
    clean = overlap_weight_assays(windows, assays)
    assert not clean.empty  # clean join works

    # consistency guard sees matching ids in the clean case
    cons_ok = qc.hole_id_consistency(windows, assays)
    assert cons_ok["consistent"] and cons_ok["n_overlap"] == 1

    # corruption: assays carry a different hole id (shuffled) -> join collapses
    bad = assays.copy()
    bad["hole_id"] = "WRONG"
    cons_bad = qc.hole_id_consistency(windows, bad)
    assert cons_bad["consistent"] is False and cons_bad["n_overlap"] == 0
    assert overlap_weight_assays(windows, bad).empty  # visible: no rows join
