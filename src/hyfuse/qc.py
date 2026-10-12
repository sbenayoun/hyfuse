"""qc.py (T1.6, T2.2): data-quality rules and assay hygiene.

Final Mask filtering (keep mask-on rows), keep 'invalid'/'aspectral' as
explicit states (not missing/zero), ignore TSAV, prefer Mineral Group for
Level 1, use 'error' as confidence. Assay hygiene: unit normalisation,
plausibility ranges, flagging (not silent dropping), below-detection handling.
"""
