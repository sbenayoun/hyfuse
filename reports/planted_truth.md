# Planted-truth study (T3.1) — what the known-answer test tells us

*Generated during T3.1. Honest record of a method investigation; informs the
real-hole ablation (T3.3) and the geologist review.*

## Setup

`src/hyfuse/synth.py` simulates holes with KNOWN mineral compositions along depth
and KNOWN domain boundaries, then applies view-specific detectability to produce
synthetic SWIR and TIR observations:

- TIR sees essentially all minerals; SWIR sees only the SWIR-active set
  (hydroxyl minerals, carbonates, sulfates), NOT anhydrous silicates.
- Chlorite is visible in BOTH views (the bridge).
- Each view reports only its detectable minerals, renormalised within the view.
- Domains differ by mineral RATIOS, split across views (a quartz:feldspar axis
  visible only to TIR; a white_mica:kaolinite axis for SWIR), plus noise,
  occasional misidentification, and aspectral windows.

The headline GSWA case is reproduced exactly: a 97% quartz / 3% chlorite window
reads **CHLORITE-dominant in SWIR** (quartz invisible) and **SILICA-dominant in
TIR**.

## What we measured

Four arms (swir_only, tir_only, concat = raw both-views, fused = per-view
compositional transform then concat), scored by how well each recovers the
planted domains — via k-means ARI and via the real pipeline's ruptures
boundary-F1. Averaged over 8-15 seeds.

## Findings

1. **View effect is correct.** The 97/3 quartz/chlorite case behaves exactly as
   GSWA describes. The simulator reproduces the core phenomenon.

2. **CLR destroys domain signal here; Hellinger preserves it.** Within a single
   view, raw-abundance k-means ARI was ~0.94 (TIR) but CLR ARI collapsed to
   ~0.06. Diagnosis: CLR's geometric-mean **centring**, with many near-zero
   mineral groups, injects absent-mineral log-ratio noise into every component.
   The **square-root (Hellinger) transform** recovered the full signal (~0.94),
   handles zeros natively, and is now the project default
   (`features.view_features(transform="hellinger")`); CLR is kept as an ablation.

3. **On this simulator, TIR alone is as strong as any fusion.** Over 15 seeds
   (consistent Hellinger transform):

   | arm | mean ARI | median | min |
   |---|---:|---:|---:|
   | swir_only | 0.46 | 0.38 | 0.17 |
   | tir_only  | 0.79 | 0.81 | 0.51 |
   | raw_concat | 0.79 | 0.82 | 0.40 |
   | fused (Hellinger) | 0.58 | 0.52 | 0.28 |

   The planted domains turned out highly TIR-separable, so TIR alone already
   captures them; adding SWIR via raw concat neither helps nor hurts, and the
   symmetric fused transform (equal footing for a weak and a strong view)
   DILUTES the strong view and under-performs. This is a property of the
   simulated domain design, not a law about real rocks.

## What we assert in the test (robust claims only)

`tests/test_planted.py` asserts only what is robust across seeds:
- the 97/3 quartz/chlorite view effect;
- the pipeline WORKS (strongest arm ARI > 0.5, well above chance);
- both multi-view arms are at least as good as the WEAKEST single view;
- all four arms run.

We deliberately do NOT assert "fusion beats the best single view" — the
simulation does not robustly support it (TIR-dominated here). Overclaiming that
would be exactly the self-deception the project is built to avoid.

## Implications for the real-hole ablation (T3.3)

- Use **Hellinger** as the default compositional transform; report CLR as an
  ablation (it under-performs).
- Report the four-arm comparison **honestly**: naive concat is a strong baseline;
  "fusion helps / does not help / inconclusive" is decided by the real holes +
  assay prediction, with hole-level bootstrap intervals, not assumed.
- A plausible real-world outcome is "both views together are no better than the
  better single view" — that is an acceptable, publishable negative result.

## For the geologist

Do real HyLogger geological domains differ mainly in mineral **ratios** (which
the compositional transforms target) and are they typically **more separable in
TIR, SWIR, or genuinely only when combined**? Our simulated domains were
TIR-dominated by construction; your sense of where the real discriminating
mineralogy lives would tell us whether a symmetric fusion should be expected to
help at all, or whether one view usually dominates.
