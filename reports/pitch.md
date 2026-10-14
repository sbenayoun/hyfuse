# HyFuse — pitch outline

GSWA HyLogger Hackathon 2026 · Data Crunch
Team: HyFuse Team · https://github.com/sbenayoun/hyfuse

> Plain outline for building the pitch deck (PowerPoint / Google Slides / Canva).
> Every number is from `reports/` — do not add any figure the pipeline did not
> generate. Add the viewer screenshot (`docs/viewer.png`) on the "What we built"
> slide. The slide PDF is a submission-form attachment and is not committed.

---

## 1. The problem

Combining SWIR and TIR HyLogger results is an unsolved problem (GSWA).

- The two sensors see different minerals: a rock that is 97% quartz / 3% chlorite
  reads quartz-dominant in TIR but chlorite-only in SWIR.
- GSWA: a good way to combine them "would be a powerful tool".

**Our question:** does fusing SWIR + TIR recover geological domains and
gold-related properties better than either view alone — on drillholes the method
has never seen?

---

## 2. What we built

A reproducible pipeline + viewer, and a four-arm ablation.

fetch → QC (Final Mask, units, below-detection) → 5 m windows → per-view
compositional features → domaining (PCA → HDBSCAN → ruptures) → score on
HELD-OUT holes.

Four arms on identical windows: SWIR only · TIR only · naive concat · fused.
Scored by boundary agreement vs logged lithology (permutation baseline) and gold
prediction (leave-holes-out CV).

(Show the viewer screenshot: `docs/viewer.png`.)

---

## 3. How we tested it (the trust story)

- Pre-registered success criteria, tolerance, CV scheme — frozen in git before
  any results.
- Leave-holes-out CV + permutation baseline + hole-level bootstrap.
- Planted-truth simulation + corruption tests (×1000 units, depth offset, ignored
  mask, shuffled IDs) that must fail loudly.
- 4 independent reviews + a calibration that planted 3 defects and confirmed the
  reviewer caught 3/3.

Built to give a trustworthy answer — positive or not.

---

## 4. The result (stated plainly)

15 gold holes → INCONCLUSIVE at our pre-registered 5 m window. Fusion is no
better than the best single view.

| arm | boundary F1 | gold Au R² (held-out) |
|---|---:|---:|
| SWIR only | 0.102 | no skill |
| TIR only | 0.139 | no skill |
| naive concat | 0.129 | no skill |
| fused | 0.140 | no skill |

- Fused − best single (TIR): +0.001, 95% CI [−0.017, +0.022] (includes zero).
- No arm predicts gold on held-out holes (all median R² ≤ 0).

A negative result, reported as plainly as a positive one would be.

---

## 4b. Sensitivity — and why we didn't move the goalposts

A geologist suggested finer windows. We ran it as a declared sensitivity
analysis (the 5 m headline stays frozen — pre-registered before any results):

| window | fused − best single | 95% CI | verdict |
|---|---:|---|---|
| 5 m (headline) | +0.001 | [−0.017, +0.022] | inconclusive |
| 1 m | +0.028 | [+0.008, +0.051] | fusion helps |
| 0.5 m | −0.016 | [−0.044, +0.015] | inconclusive |

At ~1 m fusion *does* beat the single view — but it flips back at 0.5 m. So the
honest statement is: **the fusion benefit is not robust across resolutions.** We
report the favourable 1 m slice as a sensitivity, not as the headline. Whether
the 1 m gain is real lithology or finer windows matching dense logging is an open
question for a geologist.

---

## 5. What we checked, and the limits

- Domains are not explained by processing level (confounder check).
- Planted-truth agreed: on known-answer data, TIR alone matched any fusion.
- Limits: n = 15, 11/15 one deposit (Bannockburn) + 4 regional → weak
  generality; assays are selection-biased; not yet geologically validated.

Anomalies here are "evidence worth investigating", never mineralisation.

---

## 6. What GSWA gets, and next steps

- A reproducible pipeline (`make fetch → evaluate`, bit-for-bit) + config + an
  interactive viewer, public and MIT-licensed.
- A method result: for these holes, TIR alone is as good as fusion, and
  mineralogy alone does not predict gold across holes.
- Next: more holes across different deposits; expert-labelled domains; test
  fusion where SWIR and TIR genuinely disagree (the chlorite bridge).

Repo: https://github.com/sbenayoun/hyfuse

---

## Appendix (backup)

- Why CLR failed → we use Hellinger (`reports/planted_truth.md`).
- Per-hole boundary table + permutation p-values (`reports/ablation.md`).
- The 97/3 quartz/chlorite case reproduced in simulation.
- Reviewer calibration found/missed table (`reports/calibration.md`).
