# Window-size sensitivity (added after geologist feedback, 2026-10-14)

Headline window is **5.0 m** (pre-registered, frozen before results — unchanged). This is a DECLARED sensitivity analysis showing how the fused-vs-best-single-view verdict depends on window resolution. Native HyLogger sample spacing is ~8 mm, so all windows below are achievable.


| window (m) | fused F1 | TIR F1 | SWIR F1 | concat F1 | delta (fused−best) | 95% CI | verdict |
|---:|---:|---:|---:|---:|---:|---|---|
| 5.0 (headline) | 0.140 | 0.139 | 0.102 | 0.129 | +0.001 | [-0.017, +0.022] | inconclusive |
| 1.0 | 0.262 | 0.234 | 0.233 | 0.254 | +0.028 | [+0.008, +0.051] | fusion helps |
| 0.5 | 0.337 | 0.353 | 0.322 | 0.344 | -0.016 | [-0.044, +0.015] | inconclusive |

## Reading

- The result is **sensitive to window size**. At the pre-registered 5 m it is inconclusive; at ~1 m fusion beats the best single view (CI excludes zero); at 0.5 m it is inconclusive again.
- We do NOT change the headline to 1 m: that would be a post-hoc goalpost move. The honest statement is **'any fusion benefit is not robust across resolutions; it appears only near 1 m.'**
- OPEN (for a geologist): at finer windows boundary F1 rises for ALL arms — is the ~1 m fusion gain real lithology, or finer windows matching dense company logging by chance? The permutation baseline controls per window, but the interpretation is geological.
