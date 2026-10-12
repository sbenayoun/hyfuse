-- composite_join.sql (T2.1): composite HyLogger to fixed depth windows and
-- overlap-weight assays/geology onto those windows.
--
-- Parameters (bound from Python via DuckDB named params):
--   $hole_id        : hole identifier (string)
--   $win            : window size in metres (params.yaml window_size_m, default 5.0)
--   $tidy_parquet   : path/glob to the per-hole tidy Parquet (data/derived/holes/<hole>.parquet)
--   $assays         : the assays table/view for this hole (collar-filtered, long form)
--
-- Inputs expected:
--   tidy(hole_id, depth_from, depth_to, view, mineral_group, abundance, final_mask, ...)
--   assays_long(hole_id, depth_from, depth_to, element, value)   -- below-detection resolved upstream
--
-- Output: one row per (hole_id, win_from, win_to) with:
--   - SWIR/TIR mineral-group abundance aggregates (mask-on only), and
--   - overlap-length-weighted assay means per element.
--
-- Overlap-weighting rule (plan): when several assay intervals overlap one window,
-- weight each by the length of its overlap with the window; never average blindly.

-- 1. Fixed windows spanning the hole's masked depth extent.
WITH bounds AS (
    SELECT
        min(depth_from) AS d0,
        max(depth_to)   AS d1
    FROM read_parquet($tidy_parquet)
    WHERE final_mask = 1
),
win AS (
    SELECT
        $hole_id AS hole_id,
        d0 + w * $win AS win_from,
        least(d0 + (w + 1) * $win, d1) AS win_to
    FROM bounds,
         range(0, cast(ceil((d1 - d0) / $win) AS BIGINT)) AS t(w)
    WHERE d0 + w * $win < d1
),

-- 2. Composite HyLogger mineral-group abundance per window and view
--    (mask-on rows only). Sample depth midpoint decides window membership.
tidy AS (
    SELECT *, (depth_from + depth_to) / 2.0 AS mid
    FROM read_parquet($tidy_parquet)
    WHERE final_mask = 1
),
hylog AS (
    SELECT
        w.win_from, w.win_to, t.view, t.mineral_group,
        avg(t.abundance) AS mean_abundance,
        count(*)         AS n_samples
    FROM win w
    JOIN tidy t
      ON t.mid >= w.win_from AND t.mid < w.win_to
    GROUP BY w.win_from, w.win_to, t.view, t.mineral_group
),

-- 3. Overlap-weighted assay means per window and element.
--    overlap = max(0, min(win_to,a_to) - max(win_from,a_from)).
assay_overlap AS (
    SELECT
        w.win_from, w.win_to, a.element,
        a.value,
        greatest(0.0,
            least(w.win_to, a.depth_to) - greatest(w.win_from, a.depth_from)
        ) AS overlap_len
    FROM win w
    JOIN assays_long a
      ON a.depth_from < w.win_to
     AND a.depth_to   > w.win_from
),
assay_weighted AS (
    SELECT
        win_from, win_to, element,
        sum(value * overlap_len) / nullif(sum(overlap_len), 0) AS value_wmean,
        sum(overlap_len) AS total_overlap
    FROM assay_overlap
    WHERE overlap_len > 0
    GROUP BY win_from, win_to, element
)

SELECT
    w.hole_id, w.win_from, w.win_to,
    h.view, h.mineral_group, h.mean_abundance, h.n_samples,
    aw.element, aw.value_wmean, aw.total_overlap
FROM win w
LEFT JOIN hylog h          ON h.win_from = w.win_from AND h.win_to = w.win_to
LEFT JOIN assay_weighted aw ON aw.win_from = w.win_from AND aw.win_to = w.win_to
ORDER BY w.win_from, h.view, h.mineral_group, aw.element;
