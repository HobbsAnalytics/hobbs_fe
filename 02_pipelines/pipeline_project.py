"""Blue Ridge LNG Terminal: project data ingestion, a Lakeflow Spark Declarative Pipeline (SDP).

Auto Loader streams the six synthetic project CSVs out of the landing Volume into six bronze
streaming tables; six silver materialized views then type, clean and validate them.

    /Volumes/<catalog>/<prefix>_landing/project/<dataset>.csv     (flat files, one per dataset)
        -> <catalog>.<prefix>_bronze_project.<dataset>_raw        (streaming table, raw + lineage)
        -> <catalog>.<prefix>_silver_engineering.<dataset>        (materialized view, typed + DQ)

    datasets: schedule, cost, ncrs, change_orders, safety_log, daily_reports

One pipeline writes into two schemas. Its default schema is the bronze one (set in
resources/pipeline-project.yml) and the silver datasets carry fully-qualified names, so no second
pipeline is needed. The catalog and schema prefix arrive as pipeline configuration (bundle variables
`catalog` and `schema_prefix`); the defaults below are the bundle defaults.

Data quality. Bronze has no constraints: it keeps everything the source sent. Silver enforces:
  * every primary id must be present, otherwise the row is dropped (`expect_or_drop`);
  * the schedule's `discipline` must be one of the five project disciplines, otherwise the update
    fails (`expect_or_fail`), because every downstream join and KPI is keyed on it;
  * a few warn-only `expect` checks record business-rule violations without removing rows.
Per-expectation pass/fail counts land in the pipeline event log.

Re-ingestion. Auto Loader remembers each file by path and reads it once. If the CSVs are regenerated
(for example `job_synthetic_data` with another `as_of_date`), run a full refresh to reload them:
    databricks bundle run pipeline_project -t demo --full-refresh-all --profile DEFAULT
"""

# `spark` is injected into pipeline source files by the runtime, so a linter sees it as undefined.
# ruff: noqa: F821
from pyspark import pipelines as dp
from pyspark.sql import functions as F

# --------------------------------------------------------------------------------------------------
# Configuration: where the data comes from and where it goes
# --------------------------------------------------------------------------------------------------
CATALOG = spark.conf.get("bluerridge.catalog", "mfg_mc_se_sa")
PREFIX = spark.conf.get("bluerridge.schema_prefix", "bluerridge")

LANDING = f"/Volumes/{CATALOG}/{PREFIX}_landing/project"
BRONZE = f"{CATALOG}.{PREFIX}_bronze_project"
SILVER = f"{CATALOG}.{PREFIX}_silver_engineering"

# The five disciplines the synthetic project uses. `instr` (not "instrumentation") is deliberate:
# it is the value in the CSVs and in the drawing manifest, so joins on discipline line up.
DISCIPLINES = ("mechanical", "electrical", "structural", "piping", "instr")
DISCIPLINE_IN_VOCABULARY = "discipline IN (" + ", ".join(f"'{d}'" for d in DISCIPLINES) + ")"


# ==================================================================================================
# BRONZE: raw Auto Loader streaming tables (no data-quality constraints)
# ==================================================================================================
def _landing_csv(dataset: str):
    """Stream `<dataset>.csv` from the landing Volume with Auto Loader.

    Auto Loader reads a directory, not a single file, so the load path is the Volume folder and
    `pathGlobFilter` narrows it to this dataset's file. The pipeline manages the schema location and
    checkpoint. Columns are typed by inference; values that do not fit land in `_rescued_data`.
    Lineage: `_ingest_timestamp`, `_source_file`.
    """
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.inferColumnTypes", "true")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .option("header", "true")
        .option("rescuedDataColumn", "_rescued_data")
        .option("pathGlobFilter", f"{dataset}.csv")
        .load(LANDING)
        .withColumn("_ingest_timestamp", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path"))
    )


BRONZE_PROPERTIES = {"quality": "bronze"}


@dp.table(
    name=f"{BRONZE}.schedule_raw",
    comment="Raw schedule milestones, one row per milestone, as ingested from schedule.csv.",
    table_properties=BRONZE_PROPERTIES,
)
def bronze_schedule_raw():
    return _landing_csv("schedule")


@dp.table(
    name=f"{BRONZE}.cost_raw",
    comment="Raw cost-control line items (budget, committed, actual, EAC) from cost.csv.",
    table_properties=BRONZE_PROPERTIES,
)
def bronze_cost_raw():
    return _landing_csv("cost")


@dp.table(
    name=f"{BRONZE}.ncrs_raw",
    comment="Raw non-conformance reports (NCRs), as ingested from ncrs.csv.",
    table_properties=BRONZE_PROPERTIES,
)
def bronze_ncrs_raw():
    return _landing_csv("ncrs")


@dp.table(
    name=f"{BRONZE}.change_orders_raw",
    comment="Raw change orders, each linked to a cost line, as ingested from change_orders.csv.",
    table_properties=BRONZE_PROPERTIES,
)
def bronze_change_orders_raw():
    return _landing_csv("change_orders")


@dp.table(
    name=f"{BRONZE}.safety_log_raw",
    comment="Raw site safety log (near misses, incidents, unsafe acts) from safety_log.csv.",
    table_properties=BRONZE_PROPERTIES,
)
def bronze_safety_log_raw():
    return _landing_csv("safety_log")


@dp.table(
    name=f"{BRONZE}.daily_reports_raw",
    comment="Raw free-text site daily reports, as ingested from daily_reports.csv.",
    table_properties=BRONZE_PROPERTIES,
)
def bronze_daily_reports_raw():
    return _landing_csv("daily_reports")


# ==================================================================================================
# SILVER: typed, cleaned, validated materialized views
# ==================================================================================================
# Column helpers. Each returns one SQL select-expression. Auto Loader already infers the bronze
# types; the casts pin the intended silver types and guard against drift. They use try_cast, so a
# value that cannot be converted becomes NULL instead of failing the whole update under ANSI mode
# (where an expectation covers the column, the row is then dropped or flagged).
def _text(col: str) -> str:
    """Trim; blank becomes NULL."""
    return f"nullif(trim({col}), '') AS {col}"


def _enum(col: str) -> str:
    """Trim, blank becomes NULL, lower-case: for controlled vocabularies."""
    return f"lower(nullif(trim({col}), '')) AS {col}"


def _cast(col: str, sql_type: str) -> str:
    return f"try_cast({col} AS {sql_type}) AS {col}"


# Lineage columns carried from bronze (`_rescued_data` stays behind).
LINEAGE = ["_ingest_timestamp", "_source_file"]
SILVER_PROPERTIES = {"quality": "silver"}


@dp.materialized_view(
    name=f"{SILVER}.schedule",
    comment=(
        "Typed, validated schedule milestones, one row per milestone_id. slip_days is "
        "actual_end - planned_end (NULL until the milestone finishes); depends_on_ids is the "
        "predecessor milestone ids as an array (empty for root milestones)."
    ),
    table_properties=SILVER_PROPERTIES,
)
@dp.expect_or_drop("milestone_id_not_null", "milestone_id IS NOT NULL")
@dp.expect_or_fail("discipline_in_vocabulary", DISCIPLINE_IN_VOCABULARY)
@dp.expect("planned_dates_ordered", "planned_end >= planned_start")
def silver_schedule():
    return spark.read.table(f"{BRONZE}.schedule_raw").selectExpr(
        _text("milestone_id"),
        _text("name"),
        _enum("discipline"),
        _cast("planned_start", "DATE"),
        _cast("planned_end", "DATE"),
        _cast("actual_start", "DATE"),
        _cast("actual_end", "DATE"),
        _text("depends_on"),
        "CASE WHEN nullif(trim(depends_on), '') IS NULL THEN array() "
        "ELSE split(trim(depends_on), ';') END AS depends_on_ids",
        _cast("criticality", "INT"),
        "datediff(try_cast(actual_end AS DATE), try_cast(planned_end AS DATE)) AS slip_days",
        *LINEAGE,
    )


@dp.materialized_view(
    name=f"{SILVER}.cost",
    comment=(
        "Typed, validated cost-control line items, one row per cost_id. Amounts are whole US "
        "dollars (BIGINT); variance_usd = eac_usd - budget_usd."
    ),
    table_properties=SILVER_PROPERTIES,
)
@dp.expect_or_drop("cost_id_not_null", "cost_id IS NOT NULL")
@dp.expect("variance_is_eac_minus_budget", "variance_usd = eac_usd - budget_usd")
@dp.expect("amounts_not_negative", "budget_usd >= 0 AND committed_usd >= 0 AND actual_usd >= 0")
def silver_cost():
    return spark.read.table(f"{BRONZE}.cost_raw").selectExpr(
        _text("cost_id"),
        _text("cost_code"),
        _text("description"),
        _enum("discipline"),
        _enum("category"),
        _text("area"),
        _text("vendor"),
        _cast("budget_usd", "BIGINT"),
        _cast("committed_usd", "BIGINT"),
        _cast("actual_usd", "BIGINT"),
        _cast("eac_usd", "BIGINT"),
        _cast("variance_usd", "BIGINT"),
        _cast("report_date", "DATE"),
        *LINEAGE,
    )


@dp.materialized_view(
    name=f"{SILVER}.ncrs",
    comment=(
        "Typed, validated non-conformance reports, one row per ncr_id. Severity is passed through "
        "as reported (critical, major, minor); code_reference is set on compliance NCRs."
    ),
    table_properties=SILVER_PROPERTIES,
)
@dp.expect_or_drop("ncr_id_not_null", "ncr_id IS NOT NULL")
@dp.expect("closed_not_before_raised", "closed_date IS NULL OR closed_date >= raised_date")
def silver_ncrs():
    return spark.read.table(f"{BRONZE}.ncrs_raw").selectExpr(
        _text("ncr_id"),
        _text("title"),
        _text("description"),
        _enum("discipline"),
        _enum("category"),
        _enum("severity"),
        _enum("status"),
        _text("area"),
        _cast("raised_date", "DATE"),
        _cast("due_date", "DATE"),
        _cast("closed_date", "DATE"),
        _text("raised_by"),
        _text("assigned_to"),
        _text("milestone_id"),
        _text("code_reference"),
        *LINEAGE,
    )


@dp.materialized_view(
    name=f"{SILVER}.change_orders",
    comment=(
        "Typed, validated change orders, one row per co_id, linked to cost_id. amount_usd is whole "
        "US dollars; schedule_impact_days is negative for an acceleration."
    ),
    table_properties=SILVER_PROPERTIES,
)
@dp.expect_or_drop("co_id_not_null", "co_id IS NOT NULL")
@dp.expect("decided_not_before_requested", "decided_date IS NULL OR decided_date >= requested_date")
def silver_change_orders():
    return spark.read.table(f"{BRONZE}.change_orders_raw").selectExpr(
        _text("co_id"),
        _text("cost_id"),
        _text("title"),
        _enum("reason"),
        _enum("status"),
        _cast("amount_usd", "BIGINT"),
        _cast("schedule_impact_days", "INT"),
        _cast("requested_date", "DATE"),
        _cast("decided_date", "DATE"),
        _text("requested_by"),
        *LINEAGE,
    )


@dp.materialized_view(
    name=f"{SILVER}.safety_log",
    comment=(
        "Typed, validated site safety log, one row per log_id. is_incident is true for lagging "
        "events (property damage, first aid, recordable, lost time, environmental) and false for "
        "leading indicators (near misses, unsafe acts and conditions, stop-work calls)."
    ),
    table_properties=SILVER_PROPERTIES,
)
@dp.expect_or_drop("log_id_not_null", "log_id IS NOT NULL")
@dp.expect("days_lost_not_negative", "days_lost >= 0")
def silver_safety_log():
    return spark.read.table(f"{BRONZE}.safety_log_raw").selectExpr(
        _text("log_id"),
        _cast("event_date", "DATE"),
        _enum("event_type"),
        _cast("is_incident", "BOOLEAN"),
        _enum("severity"),
        _text("area"),
        _enum("discipline"),
        _text("description"),
        _text("root_cause"),
        _text("corrective_action"),
        _text("reported_by"),
        _cast("days_lost", "INT"),
        *LINEAGE,
    )


@dp.materialized_view(
    name=f"{SILVER}.daily_reports",
    comment=(
        "Typed, validated site daily reports, one row per report_id. The narrative columns "
        "(work_summary, delays_and_issues, field_notes) are free text, passed through trimmed."
    ),
    table_properties=SILVER_PROPERTIES,
)
@dp.expect_all_or_drop(
    {
        "report_id_not_null": "report_id IS NOT NULL",
        "report_date_not_null": "report_date IS NOT NULL",
    }
)
@dp.expect("headcount_positive", "headcount > 0")
def silver_daily_reports():
    return spark.read.table(f"{BRONZE}.daily_reports_raw").selectExpr(
        _text("report_id"),
        _cast("report_date", "DATE"),
        _text("author"),
        _text("weather"),
        _cast("temp_f", "INT"),
        _cast("headcount", "INT"),
        _text("work_summary"),
        _text("delays_and_issues"),
        _text("field_notes"),
        *LINEAGE,
    )
