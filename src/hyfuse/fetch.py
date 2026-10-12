"""fetch.py (T1.4): sequential, cached NVCL/THREDDS downloads.

Sequential requests, exponential backoff on 5xx (tenacity), on-disk cache
keyed by hole ID, a log file, and a --max-holes guard. Extract only TSG
files; skip raw HyLogger files (no corrections/unmixing, and larger).

VERIFY: nvcl_kit API function names against its README before implementing.
"""
