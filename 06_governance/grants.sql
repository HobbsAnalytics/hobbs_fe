-- 06_governance/grants.sql  (source of truth for intended grants)
-- Placeholders in curly braces are filled in by apply.ipynb from widgets. A statement is run only when every
-- placeholder it uses has a value, otherwise it is listed as not applied.
--
-- GROUPS OUTCOME: the workspace groups bluerridge-pm and bluerridge-engineers could be created
-- (databricks groups create) but Unity Catalog rejected a GRANT to them with PRINCIPAL_DOES_NOT_EXIST, because
-- this workspace only resolves account-level groups and creating one needs account admin, which this demo does
-- not have. The probe groups were deleted. Nothing is granted to account users or any other broad principal.
-- The owner (joseph.hobbs@databricks.com) already holds ALL PRIVILEGES via ownership and catalog grants.
--
-- To enforce these: ask an account admin to create the two groups (or reuse existing ones), then run the notebook
-- with widgets pm_group=<name> and engineer_group=<name>.
--
-- {pm_group}: USE CATALOG is also needed and cannot be granted here, the catalog is shared and not owned by this demo.
-- Ask the catalog owner: GRANT USE CATALOG ON CATALOG mfg_mc_se_sa TO `{pm_group}`.

-- Project managers: read the gold layer only.
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `{pm_group}`;
GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `{pm_group}`;

-- Engineers: read silver and gold, and the drawing PDFs.
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_silver_engineering TO `{engineer_group}`;
GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_silver_engineering TO `{engineer_group}`;
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `{engineer_group}`;
GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `{engineer_group}`;
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_landing TO `{engineer_group}`;
GRANT READ VOLUME ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings TO `{engineer_group}`;

-- TODO (Task 24, post-deploy): the app's service principal does not exist until the app is deployed.
-- Replace {app_sp} with its application id (databricks apps get <app> -> service_principal_client_id).
-- Also needs USE CATALOG on mfg_mc_se_sa (catalog owner) and a '*' row in discipline_access (below).
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `{app_sp}`;
GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `{app_sp}`;
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `{app_sp}`;
GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `{app_sp}`;
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_landing TO `{app_sp}`;
GRANT READ VOLUME ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings TO `{app_sp}`;

-- TODO (Task 24): the app must see all of drawing_register, so add its service principal to the mapping table.
-- Without this row the row filter hides every drawing from the app.
-- INSERT INTO mfg_mc_se_sa.bluerridge_agents.discipline_access VALUES ('{app_sp}', '*');
