# Code excerpts corpus

52 short markdown files, one clause per file, that the Vector Search index `code_excerpts_vs` is built from. The app uses them to show a PM *why* a drawing failed: it looks up the clicked citation (exact `citation_label` match) and shows the plain-language summary, and a Genie or chat answer can retrieve related clauses semantically.

## Read this first: these are illustrative, not the codes

- **The five citation labels are fixed, illustrative project labels** (`ASME B16.5 §4.2`, `OSHA 1910.147`, `IBC 1005.1`, `ASME B31.3 §341`, `ASME B31.3 §322`). They are the exact strings the document-intelligence step writes to `compliance_findings.citation`. **Clause numbers are not authoritative.** For example, in the real ASME B16.5 the pressure-temperature ratings live in section 2, not 4.2. Do not use this corpus to cite a code.
- **No code text is quoted.** ASME and IBC are copyrighted, so every ASME and IBC entry is a plain-language paraphrase written for this demo (`is_paraphrase: true`). The OSHA 29 CFR 1910 entries are also written as paraphrases; OSHA text is federal and public domain, so verbatim excerpts would be allowed, but paraphrases avoid any risk of a misquote.
- Numbered sub-clauses in the related entries are likewise illustrative topic labels.

## File format

YAML front-matter, then a 2-6 sentence body:

| Field | Meaning |
|---|---|
| `citation_id` | stable slug, unique, also the file name |
| `citation_label` | the label shown in the app; for the five primary entries it is character-for-character the `compliance_findings.citation` string |
| `title` | short heading |
| `source` | `ASME B16.5`, `ASME B31.3`, `OSHA 29 CFR 1910` or `IBC` |
| `is_paraphrase` | `true` for every entry here |
| `related_flaw_type` | one of the five planted flaw types, or `none` |

Validate with `uv run --no-project --with pytest --with pyyaml python -m pytest 04_vector_search/tests`.
