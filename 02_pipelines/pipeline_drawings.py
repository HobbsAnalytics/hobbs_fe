"""Blue Ridge LNG Terminal: drawing ingestion, a Lakeflow Spark Declarative Pipeline (SDP).

Auto Loader streams the synthetic drawing PDFs out of the landing Volume, as binary files, into one
bronze streaming table; one silver materialized view tracks them by drawing id.

    /Volumes/<catalog>/<prefix>_landing/drawings/<drawing_id>.pdf      (flat folder, one PDF each)
        -> <catalog>.<prefix>_bronze_drawings.raw_files                 (streaming table, bytes)
        -> <catalog>.<prefix>_silver_engineering.drawings_raw_tracking  (materialized view, ids)

The bytes are not parsed here: document intelligence (03_doc_intelligence) reads `content`.

Same shape as pipeline_project.py, and kept apart from it (one pipeline per source family). The
pipeline's default schema is the bronze one (set in resources/pipeline-drawings.yml) and the silver
dataset carries a fully-qualified name. The catalog and schema prefix arrive as pipeline
configuration (bundle variables `catalog` and `schema_prefix`); the defaults below are the bundle
defaults.

Malformed files. binaryFile never parses a file, so Auto Loader has nothing to rescue: its schema is
fixed (path, modificationTime, length, content), it adds no `_rescued_data` column, and it rejects
`schemaEvolutionMode=rescue`. A text file renamed .pdf is therefore an ordinary row with a few bytes
in `content`, and it cannot fail the update. The pipeline supplies the quarantine marker itself,
with the meaning `_rescued_data` has in the CSV bronze tables: NULL for a file that starts with the
`%PDF-` header, a small JSON (file path and reason) for one that does not. The row is kept, nothing
is dropped, and the warn-only expectation `no_rescued_data` counts such files in the event log.
02_pipelines/tests/test_malformed_drawing.py drives this against the workspace.

Re-ingestion. Auto Loader remembers each file by path and reads it once. The generator rewrites the
same 1,200 paths on every run (seed 42), so a plain update after the first load adds nothing. If the
PDFs are regenerated with different content, or a file is deleted, run a full refresh to rebuild:
    databricks bundle run pipeline_drawings -t demo --full-refresh-all --profile DEFAULT
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

LANDING = f"/Volumes/{CATALOG}/{PREFIX}_landing/drawings"
BRONZE = f"{CATALOG}.{PREFIX}_bronze_drawings"
SILVER = f"{CATALOG}.{PREFIX}_silver_engineering"

# Every PDF starts with the five bytes `%PDF-`. In hex, because a SQL binary literal is X'<hex>'.
PDF_MAGIC_HEX = "255044462D"
IS_PDF = f"substring(content, 1, 5) = X'{PDF_MAGIC_HEX}'"


# ==================================================================================================
# BRONZE: raw Auto Loader streaming table (no constraints, nothing dropped)
# ==================================================================================================
def _not_a_pdf():
    """The `_rescued_data` value of a file that is not a PDF: its path and why it was flagged."""
    return F.to_json(
        F.struct(
            F.col("_metadata.file_path").alias("_file_path"),
            F.lit("content does not start with the %PDF- header").alias("reason"),
        )
    )


@dp.table(
    name=f"{BRONZE}.raw_files",
    comment=(
        "Raw drawing PDFs, one row per file in the landing Volume: path, modification_time, "
        "length and the file's bytes in content. Files are kept as they arrived. _rescued_data "
        "is NULL for a real PDF and a JSON reason for a file without the %PDF- header."
    ),
    table_properties={"quality": "bronze"},
)
@dp.expect("no_rescued_data", "_rescued_data IS NULL")
def bronze_raw_files():
    """Stream every `*.pdf` in the landing Volume with Auto Loader's binaryFile format.

    The binaryFile schema is fixed: path, modificationTime (renamed to modification_time here),
    length and content, so schema evolution is switched off (`none`: binaryFile rejects every
    other mode). The pipeline manages the schema location and checkpoint.
    Lineage: `_ingest_timestamp`, `_source_file`.
    """
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "binaryFile")
        .option("cloudFiles.schemaEvolutionMode", "none")
        .option("pathGlobFilter", "*.pdf")
        .load(LANDING)
        .withColumnRenamed("modificationTime", "modification_time")
        .withColumn("_rescued_data", F.when(~F.expr(IS_PDF), _not_a_pdf()))
        .withColumn("_ingest_timestamp", F.current_timestamp())
        .withColumn("_source_file", F.col("_metadata.file_path"))
    )


# ==================================================================================================
# SILVER: tracking view of the files, keyed by drawing id (no bytes)
# ==================================================================================================
@dp.materialized_view(
    name=f"{SILVER}.drawings_raw_tracking",
    comment=(
        "One row per drawing file in the landing Volume, passed through from bronze without the "
        "bytes. drawing_id is the file name without .pdf; volume_path is the /Volumes path, in "
        "the same form as volume_path in the drawing manifest."
    ),
    table_properties={"quality": "silver"},
)
@dp.expect_or_drop("drawing_id_present", "drawing_id <> ''")
def silver_drawings_raw_tracking():
    return spark.read.table(f"{BRONZE}.raw_files").select(
        F.regexp_extract("path", r"/([^/]+)\.pdf$", 1).alias("drawing_id"),
        # binaryFile reports dbfs:/Volumes/...; the manifest and the Files API use /Volumes/...
        F.regexp_replace("path", r"^dbfs:", "").alias("volume_path"),
        "length",
        "modification_time",
        "_source_file",
    )
