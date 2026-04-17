---
name: memory-reconciler
description: "Manual memory wiki reconciliation for operator-triggered use. Use when: user asks to 'reconcile memory', 'run wiki reconciliation', 'reconciler status', 'wiki reconciliation status', 'wiki status', 'check reconciler'."
---

# Memory Reconciler — Manual Reconciliation Skill

Reconciles consolidated durable memory sources into memory-wiki's isolated vault. This skill covers operator-requested reconciliation runs, status checks, and source inspection. Autonomous scheduling and setup are handled separately.

## When to Use

- Operator wants to run a reconciliation cycle now
- Operator wants to check reconciler status or last run results
- Operator wants to verify which sources are currently present
- Operator wants to inspect compile or lint results
- Operator wants to see what the reconciler would ingest

## Manual Triggers

| Command | Action |
|---------|--------|
| "Reconcile memory" / "Run wiki reconciliation" | Run full reconciliation cycle (ingest → compile → lint) |
| "Reconciler status" / "Wiki status" | Show last run, source presence, compile/lint status |
| "Dry run reconciliation" | Show what sources would be ingested without calling wiki |
| "Check reconciler sources" | List which of the four sources are present |

## Preconditions

Before manual execution:

1. Confirm workspace context — resolve paths dynamically, do not assume fixed install paths
2. Verify memory-wiki is enabled and configured for isolated vault mode
3. Verify `runtime/memory-reconciler-metadata.json` exists
4. If files are missing, point the operator to `INSTALL.md` — do not invent outputs

## Outputs

A manual run produces:

- **Wiki vault** — updated with ingested source content
- **Compiled wiki pages** — with backlinks and dashboards
- **Lint results** — warnings and reports
- **runtime/memory-reconciler-metadata.json** — updated run metadata
- **Unified memory telemetry** — one structured event appended to `TELEMETRY_ROOT/memory-log-YYYY-MM-DD.jsonl`

## What the Agent Must Not Do

- Do not run `wiki apply` or `wiki_apply`
- Do not modify any of the four source files (MEMORY.md, LTMEMORY.md, PROCEDURES.md, episodes)
- Do not create source files — only consume them if present
- Do not consolidate, score, or gate entries
- Do not write telemetry with raw shell echo — use `scripts/append_memory_log.py`
- Do not assume hardcoded paths — resolve SKILL_ROOT, WORKSPACE_ROOT, TELEMETRY_ROOT dynamically
- Do not skip telemetry even when notification is silent

## Boundaries

- This skill is for manual/operator-triggered use
- Scheduling and cron behavior are not owned by this file
- Setup and config internals are documented elsewhere
- Runtime orchestration details live in references and runtime files

## See Also

- `INSTALL.md` — installation, configuration, and first-run bootstrap
- `README.md` — package overview, ownership boundary, architecture
- `references/source-contract.md` — four-source seam definition
- `references/config-template.md` — wiki isolated vault configuration
- `references/runtime-templates.md` — telemetry schema, metadata format, path model
