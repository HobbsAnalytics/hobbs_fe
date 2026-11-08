-- 06_governance/tags.sql
-- Unity Catalog tags on every bluerridge_* schema, the key tables and a few columns. Idempotent (SET TAGS overwrites).
--
-- TAG-POLICY FINDING: this account enforces governed tags for the keys layer, sensitivity, data_class and domain,
-- with their own allowed values (layer: bronze|silver|gold, sensitivity: pii|internal|public,
-- data_class: HR values such as compensation|payroll, domain: finance|sales|supply_chain|quality|hr|operations).
-- Those policies belong to the shared account, so this project does not touch them. The project vocabulary is
-- therefore carried in project-prefixed keys that no policy governs:
--   br_layer        landing | bronze | silver | gold | agents | app
--   br_sensitivity  low | medium | high
--   br_data_class   engineering | financial | safety | ai_output | reference
--   br_domain       project_controls | document_intelligence
--   synthetic       true
-- In addition the governed key layer is set where its allowed values fit (bronze, silver and gold schemas).
-- No tag is applied to SDP-managed streaming tables or materialized views, so a pipeline refresh cannot reset it.

-- Schemas
ALTER SCHEMA mfg_mc_se_sa.bluerridge_landing SET TAGS ('br_layer' = 'landing', 'br_sensitivity' = 'low', 'br_data_class' = 'engineering', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER SCHEMA mfg_mc_se_sa.bluerridge_bronze_project SET TAGS ('layer' = 'bronze', 'br_layer' = 'bronze', 'br_sensitivity' = 'medium', 'br_data_class' = 'engineering', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER SCHEMA mfg_mc_se_sa.bluerridge_bronze_drawings SET TAGS ('layer' = 'bronze', 'br_layer' = 'bronze', 'br_sensitivity' = 'low', 'br_data_class' = 'engineering', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER SCHEMA mfg_mc_se_sa.bluerridge_silver_engineering SET TAGS ('layer' = 'silver', 'br_layer' = 'silver', 'br_sensitivity' = 'medium', 'br_data_class' = 'engineering', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER SCHEMA mfg_mc_se_sa.bluerridge_gold_pm SET TAGS ('layer' = 'gold', 'br_layer' = 'gold', 'br_sensitivity' = 'high', 'br_data_class' = 'engineering', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER SCHEMA mfg_mc_se_sa.bluerridge_agents SET TAGS ('br_layer' = 'agents', 'br_sensitivity' = 'low', 'br_data_class' = 'reference', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER SCHEMA mfg_mc_se_sa.bluerridge_app SET TAGS ('br_layer' = 'app', 'br_sensitivity' = 'low', 'br_data_class' = 'reference', 'br_domain' = 'project_controls', 'synthetic' = 'true');

-- Key tables (managed Delta tables only)
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings SET TAGS ('br_layer' = 'gold', 'br_sensitivity' = 'high', 'br_data_class' = 'ai_output', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.compliance_suppressed SET TAGS ('br_layer' = 'gold', 'br_sensitivity' = 'medium', 'br_data_class' = 'ai_output', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.compliance_eval SET TAGS ('br_layer' = 'gold', 'br_sensitivity' = 'low', 'br_data_class' = 'ai_output', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.kpi_daily SET TAGS ('br_layer' = 'gold', 'br_sensitivity' = 'high', 'br_data_class' = 'financial', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.risk_forecast SET TAGS ('br_layer' = 'gold', 'br_sensitivity' = 'high', 'br_data_class' = 'ai_output', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.schedule_overdue SET TAGS ('br_layer' = 'gold', 'br_sensitivity' = 'medium', 'br_data_class' = 'engineering', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.daily_brief SET TAGS ('br_layer' = 'gold', 'br_sensitivity' = 'high', 'br_data_class' = 'ai_output', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.drawing_register SET TAGS ('br_layer' = 'gold', 'br_sensitivity' = 'medium', 'br_data_class' = 'engineering', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_silver_engineering.drawings_parsed SET TAGS ('br_layer' = 'silver', 'br_sensitivity' = 'medium', 'br_data_class' = 'engineering', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_silver_engineering.drawings_extracted SET TAGS ('br_layer' = 'silver', 'br_sensitivity' = 'medium', 'br_data_class' = 'engineering', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_silver_engineering.ground_truth_findings SET TAGS ('br_layer' = 'silver', 'br_sensitivity' = 'low', 'br_data_class' = 'reference', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_silver_engineering.risk_series SET TAGS ('br_layer' = 'silver', 'br_sensitivity' = 'medium', 'br_data_class' = 'financial', 'br_domain' = 'project_controls', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_agents.code_excerpts SET TAGS ('br_layer' = 'agents', 'br_sensitivity' = 'low', 'br_data_class' = 'reference', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');
ALTER TABLE mfg_mc_se_sa.bluerridge_agents.discipline_access SET TAGS ('br_layer' = 'agents', 'br_sensitivity' = 'high', 'br_data_class' = 'reference', 'br_domain' = 'document_intelligence', 'synthetic' = 'true');

-- Columns
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings ALTER COLUMN reason SET TAGS ('br_data_class' = 'ai_output');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.compliance_findings ALTER COLUMN evidence_text SET TAGS ('br_data_class' = 'ai_output');
ALTER TABLE mfg_mc_se_sa.bluerridge_gold_pm.daily_brief ALTER COLUMN brief_md SET TAGS ('br_data_class' = 'ai_output');
