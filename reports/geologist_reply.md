# Reply to the geologist's feedback (results round)

Three points raised; answered below. Numbers from runnable code (window
sensitivity re-run on 2026-10-14).

## 1. What is a "boundary"? Is it the same everywhere?

There are **two kinds of boundary**, same concept (a depth where a unit changes),
different source. The report should have separated them clearly — fixed now.

- **Logged boundary** (ground truth): a depth where the *company's logged
  lithology* changes — i.e. the interior edges of the logged intervals
  (`wamex_dh_geology` FromDepth/ToDepth), excluding the hole top and bottom.
  Code: `evaluate.logged_boundaries`.
- **Detected boundary** (our model): a depth where *our method* decides one
  spectral/mineralogical **domain** ends and the next begins — a change-point in
  the per-window compositional features, found by `ruptures` PELT segmentation.
  Code: `domains._segment_boundaries`.

Both are then snapped to the window grid and matched within a 2 m tolerance
(`evaluate.snap_to_grid`, `match_boundaries`). "Boundary F1" = agreement between
the two sets. So: one definition of *boundary* (a unit change with depth), two
*sources* (log vs model). We will make this explicit in README/ablation.md.

## 2. Finer windows (down to ~10 cm) — achievable? does it change the result?

**Achievable: yes.** Native HyLogger sample spacing is ~8 mm, so a 10 cm window
still holds ~10 samples; even 1 cm is possible. 5 m was chosen only to match
GSWA's 5 m gold cut-off convention and the assay compositing, not a data limit.

**Does it change the (INCONCLUSIVE) outcome? YES — and this matters.** We re-ran
the four-arm ablation at finer windows (boundary F1; fused vs best single view,
hole-level bootstrap):

| window | fused F1 | TIR (best single) | delta (fused−TIR) | 95% CI | verdict |
|---|---:|---:|---:|---|---|
| 5 m (pre-registered) | 0.140 | 0.139 | +0.001 | [−0.017, +0.022] | inconclusive |
| **1 m** | 0.262 | 0.234 | **+0.028** | **[+0.008, +0.051]** | **fusion helps** |
| 0.5 m | 0.337 | 0.353 | −0.016 | [−0.044, +0.015] | inconclusive |

At **1 m**, fusion beats the best single view with a CI excluding zero — the
opposite of our 5 m headline. At 0.5 m it is inconclusive again. So the result is
**sensitive to window size**, which is itself a key finding.

**Important integrity note (why we won't just switch to 1 m):** our headline is
tied to the **pre-registered 5 m window** (frozen in git before any results).
Changing to 1 m *after seeing results* and claiming "fusion helps" would be a
post-hoc / moving-the-goalposts change — exactly the failure mode our independent
reviews and planted-flaw calibration are built to catch. The honest way to use
your suggestion is a **pre-registered sensitivity analysis**: report 0.5 / 1 / 5 m
side by side and state plainly that the fusion benefit appears only at ~1 m and is
not robust across resolutions. That is a stronger, more useful result than either
"inconclusive" or "fusion helps" alone.

**Question back to you:** at ~1 m, boundary F1 rises for *all* arms — is that
because real lithological contacts live at ~1 m scale, or because finer windows
simply create more boundaries that match the (very fine) company logging by
chance? Your read decides whether the 1 m "fusion helps" is geological or an
artifact of logging density. (We also need to confirm the permutation baseline
still controls for this at 1 m.)

## 3. BBDD0005 — "send me the depth profile from your model"

Yes. We generate a standalone, interactive down-hole figure per hole:
`review_figs/BBDD0005_tir.html` (and `_swir.html`) — regenerate with
`uv run python scripts/export_review_figs.py`. It shows, vs depth: the
mineral-group stacks, the model's **detected domain boundaries** (red), and the
**logged lithology boundaries** (grey) on the same axis. Opens in any browser; no
server or data access needed. Sent alongside this note.

If you'd like it at 1 m resolution too (given point 2), we can export a 1 m
version so you can compare the model's depth profile at both scales — tell us and
we'll generate it (clearly labelled as a sensitivity view, not the headline).
