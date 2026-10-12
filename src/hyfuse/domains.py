"""domains.py (T2.4): per-view domaining.

PCA -> HDBSCAN (record params) -> depth-aware segmentation with ruptures and
a minimum interval length. Also a PCA + k-means baseline (the common method).
Output per hole: domain labels, boundaries, soft membership where available.
"""
