-- 06_governance/grants.sql  (source of truth for intended grants)
-- Placeholders in curly braces are filled in by apply.ipynb from widgets. A statement is run only when every
-- placeholder it uses has a value, otherwise it is listed as not applied.
--
-- GROUPS OUTCOME: the workspace groups bluerridge-pm and bluerridge-engineers could be created
-- (databricks groups create) but Unity Catalog rejected a GRANT to them with PRINCIPAL_DOES_NOT_EXIST, because
-- this workspace only resolves account-level groups and creating one needs account admin, which this demo does
-- not have. The probe groups were deleted. This task made no direct grant to account users or any other broad principal.
-- NOTE: account users already holds USE CATALOG, USE SCHEMA, SELECT, READ VOLUME and EXECUTE on the catalog (granted by its
-- owners or inherited from the metastore), so every bluerridge_* table is already readable account-wide. The row filter on
-- drawing_register is the only access control this build adds. Acceptable because all data is synthetic.
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

-- App service principal (bluerridge-pm-copilot). Applied by scripts/post_deploy_grants.sh after every
-- `databricks bundle deploy` that (re)creates the app; it runs exactly the statements below that use {app_sp}
-- (the same comment-strip / split-on-semicolon / {placeholder} rules as apply.ipynb). Idempotent.
-- {app_sp} is the SP's application id: `databricks apps get bluerridge-pm-copilot -o json` ->
-- service_principal_client_id. It is also what current_user() returns inside the app's SQL (a UUID), which is why
-- the row-filter mapping row uses it. The joseph.hobbs@databricks.com deployer holds MANAGE on the catalog, so it
-- can grant USE CATALOG; that is the only catalog-level grant this project makes, and only to the app SP.
-- READ VOLUME needs USE SCHEMA on bluerridge_landing as well.
GRANT USE CATALOG ON CATALOG mfg_mc_se_sa TO `{app_sp}`;
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `{app_sp}`;
GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `{app_sp}`;
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `{app_sp}`;
GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `{app_sp}`;
GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_landing TO `{app_sp}`;
GRANT READ VOLUME ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings TO `{app_sp}`;

-- The app must see all of drawing_register, so its SP gets the '*' row in the row-filter mapping table.
-- Without it the row filter hides every drawing from the app. MERGE, so a re-run adds nothing.
MERGE INTO mfg_mc_se_sa.bluerridge_agents.discipline_access t
USING (SELECT '{app_sp}' AS principal, '*' AS discipline) s
ON t.principal = s.principal AND t.discipline = s.discipline
WHEN NOT MATCHED THEN INSERT (principal, discipline) VALUES (s.principal, s.discipline);
