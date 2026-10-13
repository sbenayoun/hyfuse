# HyFuse ablation (T3.3)

Transform: **hellinger**. Holes: **15**. Scored on identical windows per hole.


## Headline reading

INCONCLUSIVE on boundary recovery: fused F1 0.140 vs best single (tir_only) 0.139; bootstrap delta +0.001 [-0.017, +0.022] includes zero — no reliable difference between fusion and the best single view. Separately, NO arm predicts Au grade on held-out holes (all median R^2 <= 0) — mineralogy windows alone do not recover gold across holes (expected given assay selection bias).


## Boundary agreement vs logged lithology (mean F1 across holes)

| arm | mean boundary F1 | assay Au R^2 (median, leave-holes-out) |
|---|---:|---:|
| swir_only | 0.102 | -1.7 (no skill) |
| tir_only | 0.139 | -1.6 (no skill) |
| concat | 0.129 | -6.0 (no skill) |
| fused | 0.140 | -6.5 (no skill) |

## Fused vs best single view (hole-level bootstrap, boundary F1)

- best single view: **tir_only**
- delta (fused - best single): **+0.001** 95% CI [-0.017, +0.022] over 15 holes
- CI excludes zero: **False**

## Per-hole boundary detail (fused arm)

| hole | detected | logged | F1 | permutation p |
|---|---:|---:|---:|---:|
| BBDD0001 | 2 | 25 | 0.074 | 0.922 |
| BBDD0002 | 3 | 27 | 0.200 | 0.318 |
| BBDD0003 | 2 | 27 | 0.138 | 0.560 |
| BBDD0004 | 2 | 18 | 0.200 | 0.501 |
| BBDD0005 | 3 | 14 | 0.235 | 0.553 |
| BBDD0006 | 1 | 28 | 0.069 | 0.801 |
| BBDD0008 | 2 | 26 | 0.143 | 0.433 |
| BBDD0009 | 2 | 21 | 0.174 | 0.258 |
| BBDD0010 | 3 | 45 | 0.125 | 0.200 |
| BBDD0011 | 3 | 27 | 0.200 | 0.328 |
| BBRD0056 | 0 | 12 | 0.000 | 1.000 |
| 12DHDD0002 | 4 | 74 | 0.103 | 0.361 |
| 15SYDD0003B | 7 | 60 | 0.119 | 0.442 |
| 16CADD001 | 8 | 88 | 0.104 | 0.421 |
| BCMH0070 | 4 | 33 | 0.216 | 0.332 |

## Caveats

- Assay coverage is selection-biased (companies sample prospective intervals); Au is the only broadly-covered target.
- Logged lithology boundaries are company-specific; we score boundary agreement within tolerance, not code equality.
- Planted-truth study (reports/planted_truth.md): CLR under-performs -> Hellinger default; naive concat is a strong baseline.
- Results are over 15 gold holes, but 11/15 are ONE deposit (Bannockburn BBDD/BBRD) + 4 regional holes (12DHDD0002, 15SYDD0003B, 16CADD001, BCMH0070). Leave-holes-out across near-identical holes is a WEAK generality test — the result is effectively conditioned on one geological setting. Not general.
