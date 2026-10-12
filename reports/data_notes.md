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

## DASC package (T1.5, RESOLVED)

Extracted to data/raw/dasc/ (git-ignored) from
../datasets/INTERIM_HyLogger_Dataset_Package_GDA2020_DB.zip:
- HyLogger_Dataset_Package.sqlite (180 MB)
- DATADICTIONARY_INTERIM_Hylogger_GDA2020.pdf, METADATA_...pdf

DuckDB access CONFIRMED (plan 2A step 5 verbatim):
`INSTALL sqlite; LOAD sqlite;` then
`ATTACH '.../HyLogger_Dataset_Package.sqlite' AS dasc (TYPE sqlite, READ_ONLY);`
READ_ONLY works for the sqlite type in duckdb 1.5.6. Queries run fine.

### Tables (row counts)
- hylogger_dataset_index: 2019 (one row per HyLogger hole; ~matches THREDDS ~2000)
- wamex_dh_geology: 173600 (logged rock-type intervals), wapims_lithology: 1258
- wamex_assay_flat_data: 391415 (wide assay rows), wamex_assay_flat_metadata: 59568
- wamex_collar: 1676, wapims_collar: 206, wamex_survey: 62504, wapims_survey: 6662
- meta_build / meta_data_quality / meta_sources (provenance)
- v_* VIEWS: v_assay_flat_valid, v_dh_geology_valid, v_survey_valid,
  v_collar_summary, v_wapims_collar_summary, v_index_wamex_links,
  v_wapims_lithology_links -> curated/validated versions; prefer these where sensible.

### hylogger_dataset_index key columns
- Linkage: NVCL_HoleName, WAMEX_report_Anumber(_alternate), WAMEX_CollarId(_alternate),
  WAPIMS_report_Wnumber, Hole_name, Database.
- Processing level: LEV1_REL_D, LEV2_REL_D (release-date strings; non-null => that
  level released). VERIFY exact LEV2_REL_D semantics in the data dictionary PDF.
- Scan dates: SCAN_DATE (VNIR/SWIR), SCDATE_TIR, SCDATE_MIR.
- Commodity: COMMODITY, Commodity_vocab (harmonised), WS_TargetCommodity.
- Presence flags (TEXT '0'/'1'): Collar_data, Survey_data, Assay_data,
  Logging_data, Geophysics_data.
- Coords: Shapefile_latitude/longitude (GDA2020).

### KEY FINDING: SCDATE_TIR answers "which holes have TIR" without downloading
The index did not obviously flag TIR, but **SCDATE_TIR populated is a direct
proxy for a TIR scan**. Counts:
- has TIR (SCDATE_TIR set): 1958 / 2019
- has MIR (SCDATE_MIR set):   15 / 2019
- has Level 2 (LEV2_REL_D):  601 / 2019
- Assay_data=1: 1194 ; Logging_data=1: 1268
`VERIFY:` SCDATE_TIR is near-universal (1958/2019), which is suspiciously high
for a HyLogger-3+-only measurement. Treat it as a first-pass filter and CONFIRM
usable TIR mineral results per shortlisted hole from the actual TSG package
(as done for ETG0187), before trusting it.

### Coverage for GATE 1 (far above the ~8-hole threshold)
Holes with TIR + Assay_data=1 + Logging_data=1: **1124**. By Commodity_vocab:
gold 399, copper+gold 81, copper 53, nickel 38, gold+nickel 31, REE 18, ...
=> The four-arm ablation is viable; GATE 1 will not trigger. Gold is the default
headline commodity (399 holes); copper (53) is the organisers' example.

### Logged lithology columns (for T2.5 boundary scoring)
- wamex_dh_geology: CollarId, FromDepth, ToDepth, CompanyLithologyName,
  CompanyLithologyCodeMerged (company-specific), **GSWARockName (harmonised!)**,
  GSWARegolithName, colour/weathering. => a harmonised lithology column EXISTS;
  can score boundaries on company intervals and optionally compare GSWARockName.
- wapims_lithology: separate petroleum-well lithology table.

### Assay table (for T2.2) — units explicit in column names
wamex_assay_flat_data: CollarId, FromDepth, ToDepth, MidDepth, then ~100 element
columns already unit-suffixed: oxides *_PCT (SiO2_PCT, Al2O3_PCT, Fe2O3T_PCT,...),
trace *_PPM (Au_PPM, As_PPM, Cu_PPM, S_PPM, ...). Units explicit -> de-risks T2.2
unit errors, but still apply plausibility ranges (companies still make mistakes).
Join key to HyLogger: CollarId <- hylogger_dataset_index.WAMEX_CollarId.

### Open VERIFY (T1.5)
- Exact LEV2_REL_D meaning + any instrument-generation column (data dictionary PDF;
  no PDF reader installed yet — defer, or `uv add pypdf` if needed).
- Confirm the CollarId join path index.WAMEX_CollarId -> wamex_* on real holes.

## Open VERIFY items carried forward (earlier tasks)
- Final Mask scalar name + on/off direction on a real NVCL hole.
- Whether NVCL holes expose a cleaner processing-level flag than column suffixes.
- Confirm `D` units/datum on an NVCL hole (collar vs downhole).
- MIR carries no TSA mineral results here; ignore MIR unless real data differ.
