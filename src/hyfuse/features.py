"""features.py (T1.6, T2.3): tidy depth-aligned tables and compositional features.

Per-hole tidy Parquet: hole_id, depth_from, depth_to, view (swir|tir),
mineral_group, mineral, abundance, error, final_mask, processing_level,
instrument_gen. Per-view CLR with a documented zero strategy; never mix
SWIR and TIR abundances in one composition.
"""
