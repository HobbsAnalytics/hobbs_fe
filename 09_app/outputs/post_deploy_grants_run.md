# Post-deploy grants for the app service principal

Output of `scripts/post_deploy_grants.sh --profile DEFAULT` (verbatim; the script prints no credentials). Each run appends one section. The SP's application id and the role names are identifiers, not secrets.

## Run 2026-11-08 19:06:35 UTC

- Ran as `joseph.hobbs@databricks.com` (CLI profile `DEFAULT`), warehouse `527214d7319cb124`.
- (a) App `bluerridge-pm-copilot`: service principal application id `02a6516a-0d8f-49e9-8965-56e89fa12ad4`, display name `app-p3l9xk bluerridge-pm-copilot`.
- Postgres role for the SP: `02a6516a-0d8f-49e9-8965-56e89fa12ad4` (resource `projects/bluerridge-pm/branches/production/roles/dbrx-apps-02a6516a-0d8f-49e9-8965-56e89fa12ad4`, created by this run: no).

### (b) Unity Catalog grants and (c) row-filter mapping (`06_governance/grants.sql`, `{app_sp}` statements)

| # | Statement | Result |
|---|---|---|
| 1 | `GRANT USE CATALOG ON CATALOG mfg_mc_se_sa TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4`` | OK |
| 2 | `GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4`` | OK |
| 3 | `GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4`` | OK |
| 4 | `GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4`` | OK |
| 5 | `GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4`` | OK |
| 6 | `GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_landing TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4`` | OK |
| 7 | `GRANT READ VOLUME ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4`` | OK |
| 8 | `MERGE INTO mfg_mc_se_sa.bluerridge_agents.discipline_access t USING (SELECT '02a6516a-0d8f-49e9-8965-56e89fa12ad4' AS principal, '*' AS discipline) s ON t.principal = s.principal AND t.discipline = s.discipline WHEN NOT MATCHED THEN INSERT (principal, discipline) VALUES (s.principal, s.discipline)` | OK, num_affected_rows=1, num_updated_rows=0, num_deleted_rows=0, num_inserted_rows=1 |

#### Verify: `SHOW GRANTS \`02a6516a-0d8f-49e9-8965-56e89fa12ad4\` ON ...`

```
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON CATALOG mfg_mc_se_sa
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE CATALOG | CATALOG | mfg_mc_se_sa
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | USE CATALOG | CATALOG | mfg_mc_se_sa
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | SELECT | SCHEMA | mfg_mc_se_sa.bluerridge_gold_pm
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_gold_pm
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_agents
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | SELECT | SCHEMA | mfg_mc_se_sa.bluerridge_agents
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_agents
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_landing
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_landing
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | READ VOLUME | VOLUME | mfg_mc_se_sa.bluerridge_landing.drawings
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
```

All expected direct grants are present (USE CATALOG; USE SCHEMA + SELECT on gold_pm and agents; USE SCHEMA on landing; READ VOLUME on landing.drawings).

#### Verify: `discipline_access` rows for the SP

| principal | discipline |
|---|---|
| `02a6516a-0d8f-49e9-8965-56e89fa12ad4` | `*` |

### (d) Postgres grants (`08_lakebase/app_grants.sql`, `${APP_SP_ROLE}` = `02a6516a-0d8f-49e9-8965-56e89fa12ad4`)

Connected to `ep-silent-lake-d2qn95e6.database.us-east-1.cloud.databricks.com` database `databricks_postgres` as `joseph.hobbs@databricks.com` with a freshly generated database credential (not shown), `sslmode=require`.

| # | Statement | Result |
|---|---|---|
| 1 | `GRANT CONNECT ON DATABASE databricks_postgres TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 2 | `GRANT USAGE ON SCHEMA bluerridge_app TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 3 | `GRANT SELECT ON bluerridge_app.kpi_daily_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 4 | `GRANT SELECT ON bluerridge_app.compliance_findings_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 5 | `GRANT SELECT ON bluerridge_app.risk_forecast_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 6 | `GRANT SELECT ON bluerridge_app.schedule_overdue_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 7 | `GRANT SELECT ON bluerridge_app.daily_brief_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |

- `has_database_privilege('02a6516a-0d8f-49e9-8965-56e89fa12ad4', 'databricks_postgres', 'CONNECT')` = True
- `has_schema_privilege('02a6516a-0d8f-49e9-8965-56e89fa12ad4', 'bluerridge_app', 'USAGE')` = True

#### Verify: `\dp bluerridge_app.*` (access privileges; the SP's entries, `r` = SELECT)

| Schema | Name | Type | Owner | Access privileges (SP) | SP can SELECT | SP can INSERT |
|---|---|---|---|---|---|---|
| `bluerridge_app` | `compliance_findings_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `daily_brief_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `kpi_daily_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `risk_forecast_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `schedule_overdue_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |

`information_schema.role_table_grants` for the SP: 5 rows: compliance_findings_synced:SELECT, daily_brief_synced:SELECT, kpi_daily_synced:SELECT, risk_forecast_synced:SELECT, schedule_overdue_synced:SELECT

Postgres: CONNECT + USAGE granted, SELECT on all five `*_synced` tables, no INSERT (read-only by design).

## Run 2026-11-08 19:08:02 UTC

- Ran as `joseph.hobbs@databricks.com` (CLI profile `DEFAULT`), warehouse `527214d7319cb124`.
- (a) App `bluerridge-pm-copilot`: service principal application id `02a6516a-0d8f-49e9-8965-56e89fa12ad4`, display name `app-p3l9xk bluerridge-pm-copilot`.
- Postgres role for the SP: `02a6516a-0d8f-49e9-8965-56e89fa12ad4` (resource `projects/bluerridge-pm/branches/production/roles/dbrx-apps-02a6516a-0d8f-49e9-8965-56e89fa12ad4`, created by this run: no).

### (b) Unity Catalog grants and (c) row-filter mapping (`06_governance/grants.sql`, `{app_sp}` statements)

| # | Statement | Result |
|---|---|---|
| 1 | `` GRANT USE CATALOG ON CATALOG mfg_mc_se_sa TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 2 | `` GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 3 | `` GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 4 | `` GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 5 | `` GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 6 | `` GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_landing TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 7 | `` GRANT READ VOLUME ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 8 | `MERGE INTO mfg_mc_se_sa.bluerridge_agents.discipline_access t USING (SELECT '02a6516a-0d8f-49e9-8965-56e89fa12ad4' AS principal, '*' AS discipline) s ON t.principal = s.principal AND t.discipline = s.discipline WHEN NOT MATCHED THEN INSERT (principal, discipline) VALUES (s.principal, s.discipline)` | OK, num_affected_rows=0, num_updated_rows=0, num_deleted_rows=0, num_inserted_rows=0 |

#### Verify: `` SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON ... ``

```
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON CATALOG mfg_mc_se_sa
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE CATALOG | CATALOG | mfg_mc_se_sa
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | USE CATALOG | CATALOG | mfg_mc_se_sa
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | SELECT | SCHEMA | mfg_mc_se_sa.bluerridge_gold_pm
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_gold_pm
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_agents
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | SELECT | SCHEMA | mfg_mc_se_sa.bluerridge_agents
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_agents
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_landing
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_landing
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | READ VOLUME | VOLUME | mfg_mc_se_sa.bluerridge_landing.drawings
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
```

All expected direct grants are present (USE CATALOG; USE SCHEMA + SELECT on gold_pm and agents; USE SCHEMA on landing; READ VOLUME on landing.drawings).

#### Verify: `discipline_access` rows for the SP

| principal | discipline |
|---|---|
| `02a6516a-0d8f-49e9-8965-56e89fa12ad4` | `*` |

### (d) Postgres grants (`08_lakebase/app_grants.sql`, `${APP_SP_ROLE}` = `02a6516a-0d8f-49e9-8965-56e89fa12ad4`)

Connected to `ep-silent-lake-d2qn95e6.database.us-east-1.cloud.databricks.com` database `databricks_postgres` as `joseph.hobbs@databricks.com` with a freshly generated database credential (not shown), `sslmode=require`.

| # | Statement | Result |
|---|---|---|
| 1 | `GRANT CONNECT ON DATABASE databricks_postgres TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 2 | `GRANT USAGE ON SCHEMA bluerridge_app TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 3 | `GRANT SELECT ON bluerridge_app.kpi_daily_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 4 | `GRANT SELECT ON bluerridge_app.compliance_findings_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 5 | `GRANT SELECT ON bluerridge_app.risk_forecast_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 6 | `GRANT SELECT ON bluerridge_app.schedule_overdue_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 7 | `GRANT SELECT ON bluerridge_app.daily_brief_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |

- `has_database_privilege('02a6516a-0d8f-49e9-8965-56e89fa12ad4', 'databricks_postgres', 'CONNECT')` = True
- `has_schema_privilege('02a6516a-0d8f-49e9-8965-56e89fa12ad4', 'bluerridge_app', 'USAGE')` = True

#### Verify: `\dp bluerridge_app.*` (access privileges; the SP's entries, `r` = SELECT)

| Schema | Name | Type | Owner | Access privileges (SP) | SP can SELECT | SP can INSERT |
|---|---|---|---|---|---|---|
| `bluerridge_app` | `compliance_findings_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `daily_brief_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `kpi_daily_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `risk_forecast_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `schedule_overdue_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |

`information_schema.role_table_grants` for the SP: 5 rows: compliance_findings_synced:SELECT, daily_brief_synced:SELECT, kpi_daily_synced:SELECT, risk_forecast_synced:SELECT, schedule_overdue_synced:SELECT

Postgres: CONNECT + USAGE granted, SELECT on all five `*_synced` tables, no INSERT (read-only by design).

## Run 2026-11-09 02:53:58 UTC

- Ran as `joseph.hobbs@databricks.com` (CLI profile `DEFAULT`), warehouse `527214d7319cb124`.
- (a) App `bluerridge-pm-copilot`: service principal application id `02a6516a-0d8f-49e9-8965-56e89fa12ad4`, display name `app-p3l9xk bluerridge-pm-copilot`.
- Postgres role for the SP: `02a6516a-0d8f-49e9-8965-56e89fa12ad4` (resource `projects/bluerridge-pm/branches/production/roles/dbrx-apps-02a6516a-0d8f-49e9-8965-56e89fa12ad4`, created by this run: no).

### (b) Unity Catalog grants and (c) row-filter mapping (`06_governance/grants.sql`, `{app_sp}` statements)

| # | Statement | Result |
|---|---|---|
| 1 | `` GRANT USE CATALOG ON CATALOG mfg_mc_se_sa TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 2 | `` GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 3 | `` GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 4 | `` GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 5 | `` GRANT SELECT ON SCHEMA mfg_mc_se_sa.bluerridge_agents TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 6 | `` GRANT USE SCHEMA ON SCHEMA mfg_mc_se_sa.bluerridge_landing TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 7 | `` GRANT READ VOLUME ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings TO `02a6516a-0d8f-49e9-8965-56e89fa12ad4` `` | OK |
| 8 | `MERGE INTO mfg_mc_se_sa.bluerridge_agents.discipline_access t USING (SELECT '02a6516a-0d8f-49e9-8965-56e89fa12ad4' AS principal, '*' AS discipline) s ON t.principal = s.principal AND t.discipline = s.discipline WHEN NOT MATCHED THEN INSERT (principal, discipline) VALUES (s.principal, s.discipline)` | OK, num_affected_rows=0, num_updated_rows=0, num_deleted_rows=0, num_inserted_rows=0 |

#### Verify: `` SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON ... ``

```
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON CATALOG mfg_mc_se_sa
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE CATALOG | CATALOG | mfg_mc_se_sa
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | USE CATALOG | CATALOG | mfg_mc_se_sa
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_gold_pm
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | SELECT | SCHEMA | mfg_mc_se_sa.bluerridge_gold_pm
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_gold_pm
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_agents
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | SELECT | SCHEMA | mfg_mc_se_sa.bluerridge_agents
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_agents
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON SCHEMA mfg_mc_se_sa.bluerridge_landing
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | USE SCHEMA | SCHEMA | mfg_mc_se_sa.bluerridge_landing
  account users | USE SCHEMA | CATALOG | mfg_mc_se_sa
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
  account users | EXECUTE | CATALOG | mfg_mc_se_sa
  account users | SELECT | CATALOG | mfg_mc_se_sa
SHOW GRANTS `02a6516a-0d8f-49e9-8965-56e89fa12ad4` ON VOLUME mfg_mc_se_sa.bluerridge_landing.drawings
  02a6516a-0d8f-49e9-8965-56e89fa12ad4 | READ VOLUME | VOLUME | mfg_mc_se_sa.bluerridge_landing.drawings
  account users | READ VOLUME | CATALOG | mfg_mc_se_sa
  account users | READ METADATA | METASTORE | metastore_aws_us_east_1
```

All expected direct grants are present (USE CATALOG; USE SCHEMA + SELECT on gold_pm and agents; USE SCHEMA on landing; READ VOLUME on landing.drawings).

#### Verify: `discipline_access` rows for the SP

| principal | discipline |
|---|---|
| `02a6516a-0d8f-49e9-8965-56e89fa12ad4` | `*` |

### (d) Postgres grants (`08_lakebase/app_grants.sql`, `${APP_SP_ROLE}` = `02a6516a-0d8f-49e9-8965-56e89fa12ad4`)

Connected to `ep-silent-lake-d2qn95e6.database.us-east-1.cloud.databricks.com` database `databricks_postgres` as `joseph.hobbs@databricks.com` with a freshly generated database credential (not shown), `sslmode=require`.

| # | Statement | Result |
|---|---|---|
| 1 | `GRANT CONNECT ON DATABASE databricks_postgres TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 2 | `GRANT USAGE ON SCHEMA bluerridge_app TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 3 | `GRANT SELECT ON bluerridge_app.kpi_daily_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 4 | `GRANT SELECT ON bluerridge_app.compliance_findings_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 5 | `GRANT SELECT ON bluerridge_app.risk_forecast_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 6 | `GRANT SELECT ON bluerridge_app.schedule_overdue_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |
| 7 | `GRANT SELECT ON bluerridge_app.daily_brief_synced TO "02a6516a-0d8f-49e9-8965-56e89fa12ad4"` | GRANT |

- `has_database_privilege('02a6516a-0d8f-49e9-8965-56e89fa12ad4', 'databricks_postgres', 'CONNECT')` = True
- `has_schema_privilege('02a6516a-0d8f-49e9-8965-56e89fa12ad4', 'bluerridge_app', 'USAGE')` = True

#### Verify: `\dp bluerridge_app.*` (access privileges; the SP's entries, `r` = SELECT)

| Schema | Name | Type | Owner | Access privileges (SP) | SP can SELECT | SP can INSERT |
|---|---|---|---|---|---|---|
| `bluerridge_app` | `compliance_findings_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `daily_brief_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `kpi_daily_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `risk_forecast_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |
| `bluerridge_app` | `schedule_overdue_synced` | `partitioned table` | `databricks_writer_16407` | `"02a6516a-0d8f-49e9-8965-56e89fa12ad4"=r/"joseph.hobbs@databricks.com"` | True | False |

`information_schema.role_table_grants` for the SP: 5 rows: compliance_findings_synced:SELECT, daily_brief_synced:SELECT, kpi_daily_synced:SELECT, risk_forecast_synced:SELECT, schedule_overdue_synced:SELECT

Postgres: CONNECT + USAGE granted, SELECT on all five `*_synced` tables, no INSERT (read-only by design).

