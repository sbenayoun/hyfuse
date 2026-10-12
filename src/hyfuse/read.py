"""read.py (T1.3, T1.6): read TSG scalars, mineral results and Final Mask.

Read scalars with pytsg (unmixing results stored as scalars, often as codes
e.g. 'qtz'; Final Mask is also a scalar). Build a mineral_codes lookup
(code -> name -> group -> view); flag unmapped codes, never guess.

VERIFY: which scalar names hold the unmixing result, weights, error and
Final Mask, and whether 'invalid'/'aspectral' appear as explicit values.
"""
