"""ablation.py (T3.3): the real-hole four-arm evaluation run.

Ties together data_access + fusion + domains + evaluate, scores every arm on the
SAME windows/holes, and writes reports/ablation.md and reports/confounders.md.

Per arm, per hole: build features (Hellinger), detect domain boundaries
(ruptures), score boundary agreement vs logged lithology with a permutation
baseline. Pooled across holes: predict Au with leave-holes-out CV; run the
confounder check (processing_level, instrument_gen). Hole-level bootstrap gives
the fused-vs-best-single uncertainty. Reporting is plain-language and honest.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from hyfuse import data_access as da
from hyfuse import evaluate as ev
from hyfuse.domains import domain_view
from hyfuse.fusion import all_arms

log = logging.getLogger("hyfuse.ablation")
ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS = ROOT / "reports"

ARMS = ("swir_only", "tir_only", "concat", "fused")


def _per_hole_features(hole: str, win: float, transform: str, seed: int):
    """Return {arm: features_df} for one hole, all aligned to identical windows."""
    swir, tir = da.composited_views(hole, win)
    if swir.empty or tir.empty:
        return None
    return all_arms(swir, tir, transform=transform, seed=seed)


def run_ablation(*, transform: str | None = None,
                 write: bool = True) -> dict:
    """Run the four-arm ablation on all shortlisted holes; return results dict."""
    params = da.load_params()
    win = float(params["window_size_m"])
    seed = int(params["seed"])
    tol = float(params["depth_tolerance_m"])
    # Guard: scored tolerance must match the pre-registered value (F7). A
    # post-hoc change without a documented override is logged loudly.
    tol_guard = ev.preregistered_tolerance_ok(tol)
    if not tol_guard["ok"]:
        log.warning("SCORED TOLERANCE %.3f != pre-registered %.3f with no "
                    "override reason — post-hoc change (checklist B).",
                    tol_guard["scored"], tol_guard["preregistered"])
    n_perm = int(params["boundary_scoring"]["permutation"]["n"])
    targets = params["assay_targets"]
    plaus = params["assay_hygiene"]["plausibility_ppm"]
    transform = transform or "hellinger"
    seg_pen = 1.0
    min_iw = max(1, round(float(params["min_interval_m"]) / win))

    holes = da.hole_collar_map()

    # ---- boundary agreement per arm per hole + domain labels for confounders --
    boundary_f1 = {a: {} for a in ARMS}       # arm -> {hole: f1}
    boundary_detail = {a: {} for a in ARMS}   # arm -> {hole: full dict}
    arm_rows = {a: [] for a in ARMS}          # pooled feature rows for assay/confounder
    arm_labels = {a: [] for a in ARMS}        # per-window domain label (for confounder)
    arm_groups = {a: [] for a in ARMS}
    arm_instr = {a: [] for a in ARMS}
    arm_tirproc = {a: [] for a in ARMS}   # TIR processing level (varies: sTSAT vs sjCLST)
    assay_rows = {a: [] for a in ARMS}        # (features aligned to assay windows)
    assay_y = {a: [] for a in ARMS}
    assay_groups = {a: [] for a in ARMS}

    tidy_meta_cache: dict[str, pd.DataFrame] = {}

    for hole, collar in holes.items():
        feats_by_arm = _per_hole_features(hole, win, transform, seed)
        if feats_by_arm is None:
            log.warning("skipping %s (empty views)", hole)
            continue
        geol = da.logged_geology(collar)
        truth_bnd = ev.logged_boundaries(geol["depth_from"].to_numpy(),
                                         geol["depth_to"].to_numpy())
        # snap logged boundaries to the window grid (resolution floor); fair
        # comparison at our 5 m scale given very fine company logging.
        truth_bnd = ev.snap_to_grid(truth_bnd, win, origin=0.0)
        # per-hole confounders. instrument_gen is constant (all HL3+) and SWIR
        # processing is constant (sTSAS) across the shortlist, but TIR processing
        # level genuinely varies (sTSAT vs sjCLST) -> a real confounder axis.
        tidy = tidy_meta_cache.get(hole) or da.load_tidy(hole)
        tidy_meta_cache[hole] = tidy
        instr = str(tidy["instrument_gen"].iloc[0])
        tir_proc_series = tidy[tidy["view"] == "tir"]["processing_level"]
        tir_proc = str(tir_proc_series.iloc[0]) if len(tir_proc_series) else "unknown"

        wa = da.windowed_assays(hole, collar, win, targets, plaus)
        au_target = targets[0]
        wa_t = wa[wa["element"] == au_target] if not wa.empty else wa

        for arm in ARMS:
            feats = feats_by_arm[arm]
            if feats.empty:
                continue
            res = domain_view(feats, seed=seed, n_components=3,
                              min_cluster_size=5, min_interval_windows=min_iw,
                              seg_penalty=seg_pen)
            d0 = float(feats.index.get_level_values("win_from").min())
            d1 = float(feats.index.get_level_values("win_to").max())
            detected = ev.snap_to_grid(res.boundaries, win, origin=0.0)
            ba = ev.boundary_agreement_vs_baseline(
                detected, truth_bnd, d0, d1, tol, n_perm=n_perm, seed=seed)
            boundary_f1[arm][hole] = ba["f1"]
            boundary_detail[arm][hole] = {**ba, "n_logged": len(truth_bnd),
                                          "n_detected": len(detected)}

            # pooled rows for the confounder check (domain label per window)
            w = res.windows
            arm_rows[arm].append(feats)
            arm_labels[arm].append(w["domain"].to_numpy())
            arm_groups[arm].append(np.full(len(w), hole))
            arm_instr[arm].append(np.full(len(w), instr))
            arm_tirproc[arm].append(np.full(len(w), tir_proc))

            # assay prediction rows: align arm features to assay windows
            if not wa_t.empty:
                key = wa_t.set_index(["hole_id", "win_from", "win_to"])["value_wmean"]
                common = feats.index.intersection(key.index)
                if len(common) >= 1:
                    assay_rows[arm].append(feats.loc[common])
                    assay_y[arm].append(key.loc[common].to_numpy())
                    assay_groups[arm].append(np.full(len(common), hole))

    # ---- assay prediction (leave-holes-out) + confounders per arm -------------
    assay_result = {}
    confounder_result = {}
    for arm in ARMS:
        if assay_rows[arm]:
            X = pd.concat(assay_rows[arm]).fillna(0.0)
            y = np.concatenate(assay_y[arm])
            g = np.concatenate(assay_groups[arm])
            assay_result[arm] = ev.assay_prediction_cv(X, pd.Series(y), g, seed=seed)
        else:
            assay_result[arm] = {"r2_mean": float("nan"), "note": "no assay rows"}

        if arm_rows[arm]:
            feats_all = pd.concat(arm_rows[arm]).fillna(0.0)
            labels = np.concatenate(arm_labels[arm])
            groups = np.concatenate(arm_groups[arm])
            instr = np.concatenate(arm_instr[arm])
            tirp = np.concatenate(arm_tirproc[arm])
            # Only test confounders that actually VARY across holes; a constant
            # confounder is degenerate and gives false reassurance (R2/calibration
            # F5). Report the constant ones explicitly as 'not testable'.
            confounders = {}
            constant = {}
            for name, vals in (("instrument_gen", instr),
                               ("tir_processing_level", tirp)):
                # vary across HOLES, not just windows
                per_hole = {g: v for g, v in zip(groups, vals, strict=False)}
                if len(set(per_hole.values())) >= 2:
                    confounders[name] = vals
                else:
                    constant[name] = next(iter(set(vals.tolist())), "unknown")
            rep = ev.confounder_report(
                labels, feats_all.to_numpy(dtype=float),
                confounders, groups, seed=seed) if confounders else {}
            for name, val in constant.items():
                rep[name] = {"flag_confounded": False, "constant_value": val,
                             "note": "constant across shortlist; control cannot run"}
            confounder_result[arm] = rep

    # ---- fused vs best-single bootstrap on boundary F1 ------------------------
    def _mean(d):
        vals = [v for v in d.values() if np.isfinite(v)]
        return float(np.mean(vals)) if vals else float("nan")

    mean_f1 = {a: _mean(boundary_f1[a]) for a in ARMS}
    best_single = "swir_only" if mean_f1["swir_only"] >= mean_f1["tir_only"] else "tir_only"
    boot = ev.bootstrap_hole_delta(boundary_f1["fused"],
                                   boundary_f1[best_single],
                                   n=int(da.load_params()["bootstrap"]["n_resamples"]),
                                   seed=seed)

    results = {
        "transform": transform,
        "mean_boundary_f1": mean_f1,
        "boundary_detail": boundary_detail,
        "assay_r2": {a: assay_result[a].get("r2_median") for a in ARMS},
        "assay_detail": assay_result,
        "confounders": confounder_result,
        "best_single": best_single,
        "fused_vs_best_single_bootstrap": boot,
        "n_holes": len(holes),
        "tolerance_guard": tol_guard,
    }
    if write:
        _write_reports(results)
    return results


def _reading(results: dict) -> str:
    mf = results["mean_boundary_f1"]
    best = results["best_single"]
    boot = results["fused_vs_best_single_bootstrap"]
    fused, bs = mf["fused"], mf[best]
    # assay skill: positive median R^2 for any arm?
    r2s = [v for v in results["assay_r2"].values() if v is not None and np.isfinite(v)]
    assay_note = ""
    if r2s and max(r2s) <= 0:
        assay_note = (" Separately, NO arm predicts Au grade on held-out holes "
                      "(all median R^2 <= 0) — mineralogy windows alone do not "
                      "recover gold across holes (expected given assay selection bias).")
    if not np.isfinite(fused) or not np.isfinite(bs):
        return "Inconclusive: insufficient data to compare arms." + assay_note
    if boot["excludes_zero"] and boot["delta_mean"] > 0:
        return (f"Fusion HELPS boundary recovery: fused F1 {fused:.3f} vs best "
                f"single ({best}) {bs:.3f}; hole-level bootstrap delta "
                f"{boot['delta_mean']:+.3f} [{boot['ci_low']:+.3f}, "
                f"{boot['ci_high']:+.3f}] excludes zero." + assay_note)
    if boot["excludes_zero"] and boot["delta_mean"] < 0:
        return (f"Fusion HURTS vs the best single view ({best}): delta "
                f"{boot['delta_mean']:+.3f} [{boot['ci_low']:+.3f}, "
                f"{boot['ci_high']:+.3f}] excludes zero. Honest negative result."
                + assay_note)
    return (f"INCONCLUSIVE on boundary recovery: fused F1 {fused:.3f} vs best "
            f"single ({best}) {bs:.3f}; bootstrap delta {boot['delta_mean']:+.3f} "
            f"[{boot['ci_low']:+.3f}, {boot['ci_high']:+.3f}] includes zero — no "
            f"reliable difference between fusion and the best single view."
            + assay_note)


def _write_reports(results: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    mf = results["mean_boundary_f1"]
    ar = results["assay_r2"]
    bd = results["boundary_detail"]
    lines = ["# HyFuse ablation (T3.3)\n",
             (f"Transform: **{results['transform']}**. Holes: "
              f"**{results['n_holes']}**. Scored on identical windows per hole.\n"),
             "\n## Headline reading\n", _reading(results),
             "\n\n## Boundary agreement vs logged lithology (mean F1 across holes)\n",
             "| arm | mean boundary F1 | assay Au R^2 (median, leave-holes-out) |",
             "|---|---:|---:|"]
    for a in ARMS:
        f1 = mf[a]
        r2 = ar[a]
        f1s = f"{f1:.3f}" if np.isfinite(f1) else "n/a"
        if r2 is not None and np.isfinite(r2):
            # R^2 <= 0 means no cross-hole predictive skill; report plainly.
            r2s = f"{r2:.3f}" if r2 > -1 else f"{r2:.1f} (no skill)"
        else:
            r2s = "n/a"
        lines.append(f"| {a} | {f1s} | {r2s} |")
    boot = results["fused_vs_best_single_bootstrap"]
    lines += ["\n## Fused vs best single view (hole-level bootstrap, boundary F1)\n",
              f"- best single view: **{results['best_single']}**",
              (f"- delta (fused - best single): **{boot['delta_mean']:+.3f}** "
               f"95% CI [{boot['ci_low']:+.3f}, {boot['ci_high']:+.3f}] "
               f"over {boot['n_holes']} holes"),
              f"- CI excludes zero: **{boot['excludes_zero']}**",
              "\n## Per-hole boundary detail (fused arm)\n",
              "| hole | detected | logged | F1 | permutation p |",
              "|---|---:|---:|---:|---:|"]
    for hole, d in bd["fused"].items():
        lines.append(f"| {hole} | {d['n_detected']} | {d['n_logged']} | "
                      f"{d['f1']:.3f} | {d['permutation_p']:.3f} |")
    lines += ["\n## Caveats\n",
              ("- Assay coverage is selection-biased (companies sample "
               "prospective intervals); Au is the only broadly-covered target."),
              ("- Logged lithology boundaries are company-specific; we score "
               "boundary agreement within tolerance, not code equality."),
              ("- Planted-truth study (reports/planted_truth.md): CLR under-performs "
               "-> Hellinger default; naive concat is a strong baseline."),
              "- Results are over 15 gold holes (mostly one deposit); not general.",
              ]
    (REPORTS / "ablation.md").write_text("\n".join(lines) + "\n")

    # confounders.md
    clines = ["# Confounder check per arm (T3.3)\n",
              ("Do the detected domains reflect a technical confounder "
               "(processing level / instrument generation) rather than geology? "
               "Grouped by hole; flag = predicted above chance. A confounder that "
               "is CONSTANT across the shortlist cannot be tested and is marked "
               "so (not a pass).\n"),
              "| arm | confounder | status | cv_accuracy | majority | MI |",
              "|---|---|---|---:|---:|---:|"]
    for a in ARMS:
        creps = results["confounders"].get(a, {})
        if not creps:
            clines.append(f"| {a} | — | no data | | | |")
            continue
        for name, c in creps.items():
            if "constant_value" in c:
                clines.append(f"| {a} | {name} | constant "
                              f"({c['constant_value']}) — not testable | | | |")
            else:
                flag = "FLAGGED" if c["flag_confounded"] else "ok (not flagged)"
                clines.append(f"| {a} | {name} | {flag} | {c['cv_accuracy']:.3f} "
                              f"| {c['majority_rate']:.3f} | {c['mi']:.3f} |")
    clines += ["\n## Notes\n",
               ("- `tir_processing_level` genuinely varies across the shortlist "
                "(sTSAT on 2 holes, sjCLST on 13) → a real, testable confounder."),
               ("- `instrument_gen` (all HL3+) and SWIR processing (all sTSAS) are "
                "constant across the 15 pinned Level-2 holes → cannot be tested "
                "here; reported as constant, not as a pass.")]
    (REPORTS / "confounders.md").write_text("\n".join(clines) + "\n")


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    res = run_ablation()
    print(_reading(res))
    print("wrote reports/ablation.md and reports/confounders.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
