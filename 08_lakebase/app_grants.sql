-- Postgres grants for the app's service principal on the Lakebase hot-path tables.
--
-- Run ONCE, by Task 24 / the deploy step, AFTER `databricks bundle deploy` has created the app (so its service
-- principal exists) and AFTER the five synced tables are online. Run as the project owner (the identity that
-- created the synced tables, joseph.hobbs@databricks.com), connected to database `databricks_postgres`.
-- Idempotent: repeating a GRANT is a no-op. Re-run it after any re-sync that recreates a table (see the note near the end).
--
-- Placeholder: ${APP_SP_ROLE} is the app service principal's Postgres role, which is the SP's application
-- (client) id, e.g. 6f0c...-....  Get it with
--     databricks apps get <app-name> --profile DEFAULT -o json   ->  service_principal_client_id
-- and substitute it WITH the double quotes kept (the id starts with a digit or contains hyphens), e.g.
--     sed "s/\${APP_SP_ROLE}/$SP_CLIENT_ID/g" 08_lakebase/app_grants.sql
--
-- Why this exists: binding the database to the app (CAN_CONNECT_AND_CREATE) lets the SP connect and create its
-- own objects, but it cannot read schemas it does not own. The synced tables live in schema bluerridge_app, owned
-- by the project owner, so without these grants the app's first query fails with
--     psycopg.errors.InsufficientPrivilege: permission denied for schema bluerridge_app   (SQLSTATE 42501)
-- Read-only on purpose: never grant INSERT/UPDATE/DELETE on synced tables (writes corrupt the sync pipeline).
--
-- If the role does not exist yet (the app has not connected once), create it first:
--     databricks postgres create-role projects/bluerridge-pm/branches/production \
--       --role-id "sp-<client id>" --profile DEFAULT \
--       --json '{"spec":{"identity_type":"SERVICE_PRINCIPAL","postgres_role":"<client id>","auth_method":"LAKEBASE_OAUTH_V1"}}'

GRANT CONNECT ON DATABASE databricks_postgres TO "${APP_SP_ROLE}";
GRANT USAGE ON SCHEMA bluerridge_app TO "${APP_SP_ROLE}";

GRANT SELECT ON bluerridge_app.kpi_daily_synced           TO "${APP_SP_ROLE}";
GRANT SELECT ON bluerridge_app.compliance_findings_synced TO "${APP_SP_ROLE}";
GRANT SELECT ON bluerridge_app.risk_forecast_synced       TO "${APP_SP_ROLE}";
GRANT SELECT ON bluerridge_app.schedule_overdue_synced    TO "${APP_SP_ROLE}";
GRANT SELECT ON bluerridge_app.daily_brief_synced         TO "${APP_SP_ROLE}";

-- NO `ALTER DEFAULT PRIVILEGES` here, on purpose. The synced tables are owned by the sync writer role
-- (databricks_writer_<id>), and default privileges only cover objects created by the role they are set FOR;
-- setting them FOR that role is refused to the project owner ("permission denied to change default privileges"),
-- and setting them for the owner's own role would not match anything. If a SNAPSHOT re-sync ever drops and
-- recreates a table (the grant on it is then lost), simply re-run this file: it is idempotent. The app's
-- /healthz check in Task 19 should query one synced table so a lost grant is noticed at once.

-- Verify (as the owner):
--   SELECT grantee, table_name, privilege_type FROM information_schema.role_table_grants
--    WHERE table_schema = 'bluerridge_app' AND grantee = '${APP_SP_ROLE}' ORDER BY table_name;
