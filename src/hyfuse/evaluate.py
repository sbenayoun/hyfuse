"""evaluate.py (T2.5, T2.6, T3.3): scoring on identical held-out splits.

Boundary agreement vs logs (with permutation baseline); assay-target
prediction (ridge/PLS/HistGradientBoosting, GroupKFold by hole, report error
and calibration); domain stability across folds; confounder check
(processing_level, instrument_gen). Hole-level bootstrap CIs. Writes
reports/ablation.md with a plain-language reading.
"""
