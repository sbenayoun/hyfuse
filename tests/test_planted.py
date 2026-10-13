"""T3.1 planted-truth tests.

Known-answer validation BEFORE touching real holes (AGENT_INSTRUCTIONS T3.1).

What the simulation supports and we therefore assert (see reports/planted_truth.md
for the study behind these choices):
  1. The GSWA 97% quartz / 3% chlorite case: SWIR reads chlorite-dominant (quartz
     invisible), TIR reads silica-dominant.
  2. The pipeline WORKS: the strongest arm recovers known domains well above
     chance.
  3. Both multi-view arms (concat, fused) are at least as good as the WEAKEST
     single view -> adding the second view does not hurt.
  4. All four arms run on synthetic data.

Honest finding carried into the real ablation (NOT asserted as success): on this
simulator the domains are highly TIR-separable, so TIR alone is as strong as any
fusion, and the symmetric Hellinger-fused arm (equal footing for a weak and a
strong view) under-performs the best single view. Whether fusion beats the best
single view is decided by the REAL-hole ablation + assay prediction, and the
CLR-vs-Hellinger-vs-concat comparison is reported there, not assumed.
"""

import numpy as np
import yaml
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score

from hyfuse.fusion import all_arms
from hyfuse.synth import DEFAULT_MINERALS, SWIR_ACTIVE, simulate_hole


def _ari(features, truth, k, seed=0):
    if features.empty or features.shape[1] == 0:
        return -1.0
    y = np.array([truth[i] for i in features.index])
    km = KMeans(n_clusters=min(k, len(features)), random_state=seed, n_init=10)
    return adjusted_rand_score(y, km.fit_predict(features.to_numpy(dtype=float)))


def _mean_arm_ari(n_seeds=8, n_domains=4):
    scores: dict[str, list[float]] = {}
    for seed in range(n_seeds):
        h = simulate_hole(n_windows=80, n_domains=n_domains, seed=seed)
        truth = {i: int(d) for i, d in
                 zip(h.truth.index, h.truth["domain"], strict=False)}
        arms = all_arms(h.swir, h.tir, seed=0)
        for name, feats in arms.items():
            scores.setdefault(name, []).append(_ari(feats, truth, n_domains))
    return {k: float(np.mean(v)) for k, v in scores.items()}


def test_planted_quartz_chlorite_case():
    h = simulate_hole(seed=1)
    swir0, tir0 = h.swir.iloc[0], h.tir.iloc[0]
    assert "SILICA" not in h.swir.columns          # SWIR cannot see quartz
    assert swir0.get("CHLORITE", 0) > 0.5          # chlorite dominates SWIR
    assert tir0["SILICA"] > 0.8                    # quartz/silica dominates TIR


def test_four_arms_run_on_synthetic():
    h = simulate_hole(seed=2)
    arms = all_arms(h.swir, h.tir, seed=0)
    assert set(arms) == {"swir_only", "tir_only", "concat", "fused"}
    for name, feats in arms.items():
        assert feats.shape[0] > 0 and feats.shape[1] > 0, name


def test_method_works_above_chance():
    """Sanity: the strongest arm recovers known domains well above chance.
    (On this simulator TIR is highly separable, so the best single view is very
    strong; this asserts the pipeline works, not that fusion wins.)"""
    m = _mean_arm_ari()
    best = max(m.values())
    assert best > 0.5, f"no arm beats chance meaningfully; {m}"


def test_both_multiview_arms_beat_weakest_single_view():
    """Adding the second view does not hurt relative to the weakest single view
    (the robust planted-truth claim; whether fusion beats the BEST single view
    is reported from the real-hole ablation, not asserted here)."""
    m = _mean_arm_ari()
    weakest = min(m["swir_only"], m["tir_only"])
    assert m["concat"] >= weakest and m["fused"] >= weakest, m


def test_swir_active_set_matches_params():
    from pathlib import Path
    params = yaml.safe_load(Path("config/params.yaml").read_text())
    assert set(SWIR_ACTIVE) == set(params["swir_active_minerals"])
    assert "swir" in DEFAULT_MINERALS["chlorite"]["views"]
    assert "tir" in DEFAULT_MINERALS["chlorite"]["views"]   # chlorite = bridge
