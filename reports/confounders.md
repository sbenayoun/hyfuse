# Confounder check per arm (T3.3)

Do the detected domains reflect a technical confounder (processing level / instrument generation) rather than geology? Grouped by hole; flag = predicted above chance. A confounder that is CONSTANT across the shortlist cannot be tested and is marked so (not a pass).

| arm | confounder | status | cv_accuracy | majority | MI |
|---|---|---|---:|---:|---:|
| swir_only | tir_processing_level | ok (not flagged) | 0.503 | 0.748 | 0.125 |
| swir_only | instrument_gen | constant (HL3+) — not testable | | | |
| tir_only | tir_processing_level | ok (not flagged) | 0.691 | 0.748 | 0.077 |
| tir_only | instrument_gen | constant (HL3+) — not testable | | | |
| concat | tir_processing_level | ok (not flagged) | 0.737 | 0.748 | 0.143 |
| concat | instrument_gen | constant (HL3+) — not testable | | | |
| fused | tir_processing_level | ok (not flagged) | 0.740 | 0.748 | 0.078 |
| fused | instrument_gen | constant (HL3+) — not testable | | | |

## Notes

- `tir_processing_level` genuinely varies across the shortlist (sTSAT on 2 holes, sjCLST on 13) → a real, testable confounder.
- `instrument_gen` (all HL3+) and SWIR processing (all sTSAS) are constant across the 15 pinned Level-2 holes → cannot be tested here; reported as constant, not as a pass.
