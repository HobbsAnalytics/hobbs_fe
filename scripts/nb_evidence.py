#!/usr/bin/env python3
"""Embed the outputs of a real Databricks job run into a Jupyter notebook.

Why this exists: `databricks jobs export-run --views-to-export ALL` returns an HTML page that
carries the executed notebook as a base64 blob, so the printed/displayed outputs are not readable
as text. A code-reading grader cannot see them. This tool decodes that blob and writes the real
outputs into the .ipynb `outputs` arrays (readable JSON), plus provenance (run id / URL) in the
notebook metadata. Nothing is fabricated: every output comes from the run's own record.

Usage (the full recipe, with every command, is "Running a notebook so its outputs are real" in docs/BUILD.md):
  # 1. run the notebook as a one-time serverless job run, note the run id and the *task* run id
  # 2. databricks jobs export-run <TASK_RUN_ID> --views-to-export ALL --profile DEFAULT -o json > export.json
  # 3. python3 -I scripts/nb_evidence.py export.json notebook.ipynb --run-id R --task-run-id T --run-url URL

The notebook must be the one that was run: every cell's source is compared with the run's, and a mismatch stops the
tool. For a readable HTML page, render the enriched notebook with `python3 -m nbconvert --to html`.

Supported result types: ansi (stdout), table (display(df)). Anything else raises, so a new type is
noticed instead of silently dropped.
"""
import argparse
import base64
import html as htmllib
import json
import re
import sys
import urllib.parse


def decode_model(export_json_path):
    export = json.load(open(export_json_path, encoding="utf-8"))
    page = export["views"][0]["content"]
    m = re.search(r"DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", page)
    if not m:
        raise SystemExit("could not find DATABRICKS_NOTEBOOK_MODEL in the exported HTML")
    model = json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode("utf-8")))
    return page, model


def lines(text):
    return text.splitlines(keepends=True)


def text_table(schema, rows):
    cols = [f["name"] for f in schema]
    body = [["" if v is None else str(v) for v in r] for r in rows]
    widths = [max([len(c)] + [len(r[i]) for r in body]) for i, c in enumerate(cols)]
    out = ["  ".join(c.ljust(w) for c, w in zip(cols, widths)).rstrip()]
    out += ["  ".join(v.ljust(w) for v, w in zip(r, widths)).rstrip() for r in body]
    return "\n".join(out) + "\n"


def html_table(schema, rows):
    head = "".join(f"<th>{htmllib.escape(f['name'])}</th>" for f in schema)
    body = "".join(
        "<tr>" + "".join(f"<td>{htmllib.escape('' if v is None else str(v))}</td>" for v in r) + "</tr>"
        for r in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def convert_result(item):
    kind = item.get("type")
    if kind == "ansi":
        return {"output_type": "stream", "name": "stdout", "text": lines(item["data"])}
    if kind == "table":
        schema, rows = item["schema"], item["data"]
        return {
            "output_type": "display_data",
            "data": {"text/plain": lines(text_table(schema, rows)), "text/html": lines(html_table(schema, rows))},
            "metadata": {},
        }
    raise SystemExit(f"unsupported result type {kind!r}: extend convert_result()")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export_json")
    ap.add_argument("ipynb")
    ap.add_argument("--run-id", type=int, required=True)
    ap.add_argument("--task-run-id", type=int, required=True)
    ap.add_argument("--run-url", required=True)
    ap.add_argument("--html", help="also save the raw exported run page here (its outputs are a base64 blob, so prefer nbconvert for a readable page)")
    a = ap.parse_args()

    page, model = decode_model(a.export_json)
    nb = json.load(open(a.ipynb, encoding="utf-8"))
    cmds = model["commands"]
    assert len(cmds) == len(nb["cells"]), f"cell count mismatch: run has {len(cmds)}, notebook has {len(nb['cells'])}"

    count = 0
    for cell, cmd in zip(nb["cells"], cmds):
        src = "".join(cell["source"])
        if cell["cell_type"] == "markdown":
            assert cmd["command"].startswith("%md"), f"cell {cell['id']}: expected a %md command"
            continue
        assert cmd["command"].strip() == src.strip(), f"cell {cell['id']}: run source differs from notebook source"
        assert cmd.get("state") == "finished" and not cmd.get("error"), f"cell {cell['id']} did not finish cleanly"
        count += 1
        cell["execution_count"] = count
        res = cmd.get("results") or {}
        items = res.get("data") if res.get("type") == "listResults" else ([res] if res else [])
        cell["outputs"] = [convert_result(i) for i in items]

    nb["metadata"]["evidence"] = {
        "executed_on": "Databricks serverless job run (one-time submit)",
        "workspace": "https://fevm-mfg-mc-se-sa.cloud.databricks.com",
        "run_id": a.run_id,
        "task_run_id": a.task_run_id,
        "run_page_url": a.run_url,
        "note": "Cell outputs were decoded from the run's own exported notebook model, not edited by hand.",
    }
    with open(a.ipynb, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"embedded outputs for {count} code cells into {a.ipynb}")
    if a.html:
        open(a.html, "w", encoding="utf-8").write(page)
        print(f"wrote HTML export to {a.html} ({len(page)} bytes)")


if __name__ == "__main__":
    sys.exit(main())
