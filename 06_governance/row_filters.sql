-- 06_governance/row_filters.sql
-- Row-level security for the drawing register, by engineering discipline.
-- Idempotent: safe to run repeatedly. One statement per semicolon (the notebook splits on it).
-- NOTE: no filter or mask goes on kpi_daily, compliance_findings or risk_forecast (Lakebase sync sources
-- cannot be filtered or masked) nor on any table a pipeline or notebook reads.

-- 1. Gold table: one row per drawing (1,200), the only table that carries a row filter.
CREATE OR REPLACE TABLE mfg_mc_se_sa.bluerridge_gold_pm.drawing_register (
  drawing_id STRING NOT NULL COMMENT 'Drawing id, e.g. BRL-PIP-ISO-0042. Primary key (informational)',
  discipline STRING COMMENT 'mechanical, electrical, structural, piping or instr. NULL when the title block was not recognised. The row filter keys on this column',
  revision STRING COMMENT 'Current revision letter from the title block',
  drawing_type STRING COMMENT 'ISO, PID, GA, SPEC or OTHER',
  volume_path STRING COMMENT 'Unity Catalog Volume path of the PDF',
  latest_review_date DATE COMMENT 'Date of the most recent compliance review of this drawing',
  latest_status STRING COMMENT 'Drawing-level result: FAIL if any rule failed, REVIEW if the judge could not decide, otherwise PASS',
  fail_count INT COMMENT 'Number of FAIL findings on this drawing',
  computed_at TIMESTAMP COMMENT 'When this register row was computed',
  CONSTRAINT drawing_register_pk PRIMARY KEY (drawing_id)
)
COMMENT 'One row per drawing with its latest compliance status. Row-filtered by discipline via bluerridge_agents.rf_drawing_discipline. Synthetic data.';

INSERT INTO mfg_mc_se_sa.bluerridge_gold_pm.drawing_register
SELECT
  d.drawing_id,
  d.discipline,
  d.revision,
  d.drawing_type,
  coalesce(f.volume_path, concat('/Volumes/mfg_mc_se_sa/bluerridge_landing/drawings/', d.drawing_id, '.pdf')) AS volume_path,
  f.latest_review_date,
  CASE WHEN coalesce(f.fail_count, 0) > 0 THEN 'FAIL'
       WHEN coalesce(f.review_count, 0) > 0 THEN 'REVIEW'
       ELSE 'PASS' END AS latest_status,
  CAST(coalesce(f.fail_count, 0) AS INT) AS fail_count,
  current_timestamp() AS computed_at
FROM mfg_mc_se_sa.bluerridge_silver_engineering.drawings_extracted d
LEFT JOIN (
  SELECT drawing_id,
         max(volume_path) AS volume_path,
         max(review_date) AS latest_review_date,
         count(CASE WHEN status = 'FAIL' THEN 1 END) AS fail_count,
         count(CASE WHEN status = 'REVIEW' THEN 1 END) AS review_count
  FROM mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings
  GROUP BY drawing_id
) f ON f.drawing_id = d.drawing_id;

-- 2. Mapping table: which principal may see which discipline. '*' means every discipline.
CREATE TABLE IF NOT EXISTS mfg_mc_se_sa.bluerridge_agents.discipline_access (
  principal STRING NOT NULL COMMENT 'User email or service principal application id',
  discipline STRING NOT NULL COMMENT 'A discipline name, or * for all disciplines'
)
COMMENT 'Row-level security mapping for drawing_register. The two example.com rows are fictitious demo principals.';

MERGE INTO mfg_mc_se_sa.bluerridge_agents.discipline_access t
USING (
  SELECT * FROM VALUES
    ('joseph.hobbs@databricks.com', '*'),
    ('mech.engineer@example.com', 'mechanical'),
    ('piping.lead@example.com', 'piping')
  AS s(principal, discipline)
) s
ON t.principal = s.principal AND t.discipline = s.discipline
WHEN NOT MATCHED THEN INSERT (principal, discipline) VALUES (s.principal, s.discipline);

-- 3. Helper: true when a mapping row grants the discipline (exact match or *).
CREATE OR REPLACE FUNCTION mfg_mc_se_sa.bluerridge_agents.discipline_allowed(principal STRING, discipline STRING)
RETURNS BOOLEAN
COMMENT 'True if discipline_access has a row for principal with discipline = * or an exact match. NULL discipline matches only *.'
RETURN EXISTS (
  SELECT 1 FROM mfg_mc_se_sa.bluerridge_agents.discipline_access a
  WHERE a.principal = discipline_allowed.principal
    AND (a.discipline = '*' OR a.discipline = discipline_allowed.discipline)
);

-- 4. Row filter function: the caller sees a row only if the helper allows it.
CREATE OR REPLACE FUNCTION mfg_mc_se_sa.bluerridge_agents.rf_drawing_discipline(discipline STRING)
RETURNS BOOLEAN
COMMENT 'Row filter for drawing_register: discipline_allowed(current_user(), discipline).'
RETURN mfg_mc_se_sa.bluerridge_agents.discipline_allowed(current_user(), discipline);

-- 5. Attach the filter.
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.drawing_register
SET ROW FILTER mfg_mc_se_sa.bluerridge_agents.rf_drawing_discipline ON (discipline);
