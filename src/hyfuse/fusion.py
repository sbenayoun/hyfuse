"""fusion.py (T3.2): the four ablation arms.

1. SWIR only  2. TIR only  3. Naive concatenation (straw man)
4. Fused v1: per-view CLR -> per-view PCA -> scale each block to equal total
   variance -> concatenate scores.
Stretch: assay-anchored calibration; chlorite bridge-mineral check.
"""
