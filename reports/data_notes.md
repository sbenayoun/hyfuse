# reports/data_notes.md — evidenced notes on the TSG data (T1.2/T1.3)

Source of evidence: offline read of the pytsg example hole
`../pytsg/example_data/PE257D` with `pytsg==1.0.0` via
`scripts/explore_tsg.py`. No NVCL download yet. These findings must be
re-confirmed on a real NVCL hole (see VERIFY items).

## How to read a TSG package (confirmed)

`pytsg.read_tsg(folder)` -> `TSG` with `.nir`, `.tir`, `.mir`, `.cras`,
`.lidar`. Each spectral view is a `Spectra` with:
- `.spectra` (ndarray), `.wavelength` (ndarray),
- `.scalars` (**DataFrame — unmixing results live here**),
- `.classes` (dict of `ClassHeaders`; class id -> label definitions),
- `.sampleheaders` (**depth lives here**), `.bandheaders`.

NOTE: `.nir` holds the full VNIR+SWIR range (see below); there is no separate
`.swir` attribute. SWIR mineral results are the `sTSAS` columns in `.nir`.

## Spectral ranges (PE257D, measured)

| view | wavelength range | bands | top mineral group |
|------|------------------|-------|-------------------|
| nir  | 380 - 2500 nm (VNIR+SWIR) | 531 | WHITE-MICA / KAOLIN |
| tir  | 5350 - 15000 nm | 387 | SILICA (Quartz) |
| mir  | 2000 - 5348 nm  | 559 | (no TSA mineral results in this hole) |

Confirms the brief: SWIR sees hydroxyl minerals; TIR sees silica/silicates.

## Mineral results = decoded strings (better than expected)

pytsg already decodes the class-coded integers to **mineral name strings**,
so no manual `qtz`-style code lookup is needed for TSG-sourced results.
Column naming convention (TSG standard), suffix = processing method:

- SWIR (in `.nir`): `Min1/2/3 sTSAS`, `Grp1/2/3 sTSAS`, `Wt1/2/3 sTSAS`,
  `Error sTSAS`, `SNR sTSAS`. Also `sTSAV` columns = **TSAV, IGNORE per plan**.
- TIR (in `.tir`): `Min1/2/3 sTSAT` (system) and `uTSAT` (unconstrained);
  `Grp*`, `Wt*`, `Error`, `SNR` likewise. sTSA/uTSA = processing levels.

`Min1` = top mineral name; `Grp1` = **harmonised mineral group** (clean codes:
WHITE-MICA, KAOLIN, SILICA, SMECTITE, PLAGIOCLASE, PYROXENE, SULPHATE, ...).
Use `Grp1` for Level 1 per plan — it is already a tidy categorical.
`Wt1` = abundance/weight of the top mineral; `Error` = confidence.

### Special / non-mineral class values (how 'invalid'/'aspectral'/mask appear)

The minerals class list includes explicit non-mineral states, e.g. SWIR
`S_SWIR_TSA705 Minerals` ids 55-60 and TIR `S_TIR_TSA708 Minerals` ids
114-119: **Aspectral, NotInLibrary, Dark, Noisy, HighError, MaskedOff**.
Group column also has **INVALID** and **NOTAROK** (not-a-rock). So:
- `aspectral` / `invalid` appear as explicit `Min1`/`Grp1` values — keep them
  as explicit states, do NOT coerce to missing/zero (matches plan T1.6).
- `MaskedOff` as a `Min1` value is one way the mask shows up (see Final Mask).

## CRITICAL: null sentinel in numeric scalars

`Wt1` and `Error` contain the float32 sentinel **-3.40282e38** on
masked/invalid rows, which drags naive means to -inf. The pipeline MUST
treat `-3.4e38` (and large-magnitude sentinels) as null before any stats or
compositional transform. This is a built-in corruption trap -> add to QC
(qc.py) and to the corruption tests (T2.7). Valid `Wt1` is in [0, 1];
valid `Error` here is in roughly [0, 1000].

## Depth

`Spectra.sampleheaders` columns: `sample, T(tray), L, P, D, X, H(holeid)`.
**`D` = downhole depth in metres** (PE257D starts ~65.9 m). `X` appears to be
along-core position. Use `D` for depth alignment in read.py/features.py.

## Final Mask (RESOLVED on a real NVCL hole: ETG0187)

Confirmed on the real NVCL hole ETG0187 (fetched via fetch.py, T1.4):
there IS a dedicated **`Final Mask`** scalar column, present in BOTH the
NIR and TIR sections. It is binary float32 (1.0 / 0.0).

- ETG0187: 1744 rows `Final Mask == 1.0`, 1091 rows `== 0.0`, identical counts
  in NIR and TIR (same mask applied to both views).
- Direction (evidenced): the 1091 masked-off (0.0) rows coincide with the
  ~1110 EMPTY-string `Min1`/`Grp1` values -> masked-off rows carry no mineral
  result. So **`Final Mask == 1.0` = KEEP (clean core); `0.0` = DROP.**
  Matches plan T1.6. STILL VERIFY by plotting mask vs core photo once, but the
  row-count alignment is strong evidence.
- The CSIRO example hole (PE257D) did NOT have this column; it only appears on
  NVCL-processed packages. So test Final Mask handling against a real NVCL hole,
  not the pytsg example.

### Processing-level naming varies per hole (confirmed)
- PE257D (CSIRO example): SWIR `sTSAS`/`sTSAV`, TIR `sTSAT`/`uTSAT`.
- ETG0187 (NVCL): SWIR `sTSAS`/`uTSAS`/`sTSAV`, TIR `sjCLST`/`ujCLST` (CLST
  classifier variant). => read scalar column suffixes per hole; do not hardcode
  one processing-level name. `s*`=system/constrained, `u*`=unconstrained.

### Complementarity on real data (ETG0187)
- SWIR top groups: KAOLIN, WHITE-MICA, SULPHATE, CHLORITE (hydroxyl minerals).
- TIR top groups: SILICA (Quartz 1452), KAOLIN, CARBONATE, WHITE-MICA.
  TIR sees the quartz SWIR cannot -> the exact HyFuse premise, visible in data.

## Final Mask (original note, pytsg example PE257D)

No standalone "Final Mask" scalar column in this example hole. Candidates:
1. the `MaskedOff` **class value** appearing in `Min1`/`Grp1`;
2. a dedicated Final Mask scalar present on NVCL-processed holes but not this
   CSIRO example package.
`sec_end_mask` is unrelated (section-geometry marker, not Final Mask).
VERIFY: on a real GSWA NVCL hole, find the Final Mask scalar / mechanism and
confirm its on/off direction (plot against core photo or spectra) before
applying it everywhere (plan T1.6).

## Open VERIFY items carried forward
- Final Mask scalar name + on/off direction on a real NVCL hole.
- Whether NVCL holes expose a cleaner processing-level flag than column suffixes.
- Confirm `D` units/datum on an NVCL hole (collar vs downhole).
- MIR carries no TSA mineral results here; ignore MIR unless real data differ.
