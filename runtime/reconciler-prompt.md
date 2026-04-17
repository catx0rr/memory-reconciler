# Memory Reconciler — Scheduled Reconciliation

Recurring cron execution prompt. Runs 2x weekly — Wednesday 23:00 and Sunday 23:00.

---

## Canonical Source Seam

This package ingests **only** these four source types:

| Source | Path | Owner |
|--------|------|-------|
| Active durable memory | `$WORKSPACE_ROOT/MEMORY.md` | memory-core |
| Reflective long-horizon memory | `$WORKSPACE_ROOT/LTMEMORY.md` | Reflections |
| Procedural memory | `$WORKSPACE_ROOT/PROCEDURES.md` | Reflections |
| Episodic narratives | `$WORKSPACE_ROOT/memory/episodes/*.md` | Reflections |

---

## Non-Goals

- Do **not** ingest raw daily notes (`memory/YYYY-MM-DD.md`)
- Do **not** ingest dream reports (`DREAMS.md`)
- Do **not** mutate source files — ingestion is read-only
- Do **not** call `wiki apply` or `wiki_apply`
- Do **not** consolidate, score, or gate entries
- Do **not** create source files

---

## Path Resolution

Resolve these roots before any execution. Do not hardcode paths.

```
SKILL_ROOT     = absolute path of the parent of runtime/ (this file's parent dir)
SCRIPTS_DIR    = $SKILL_ROOT/scripts
WORKSPACE_ROOT = current working directory
TELEMETRY_ROOT = resolve by precedence:
                 1. RECONCILER_TELEMETRY_ROOT env var
                 2. MEMORY_TELEMETRY_ROOT env var
                 3. ~/.openclaw/telemetry fallback
```

---

## Step 1: Run reconciliation [SCRIPT]

```bash
python3 $SCRIPTS_DIR/reconcile.py --workspace $WORKSPACE_ROOT
```

Read the JSON output:

- `status` — `"ok"`, `"skipped"`, or `"error"`
- `sources_found` — list of discovered source files
- `sources_ingested` — count of successfully ingested root sources
- `episodes_found` — count of episode files found
- `episodes_ingested` — count of episode files successfully ingested
- `compile.status` — compile result
- `lint.status` — lint result
- `ingest_errors` — list of any ingest failures (partial failures are ok)
- `error` — error message if overall status is `"error"`

If `status == "skipped"` (all sources absent): proceed to Step 2 with skip telemetry.

---

## Step 2: Append telemetry [SCRIPT]

Always write telemetry regardless of run outcome or notification setting.

### On success (`status == "ok"`):

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status ok \
  --event run_completed \
  --mode scheduled \
  --details-json '{"sources_found": <list>, "sources_ingested": <N>, "episodes_found": <N>, "episodes_ingested": <N>, "compile_status": "<status>", "lint_status": "<status>"}'
```

### On skip (`status == "skipped"`):

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status skipped \
  --event run_skipped \
  --mode scheduled
```

### On error (`status == "error"`):

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status error \
  --event run_failed \
  --mode scheduled \
  --error "<error message from reconcile output>"
```

---

## Step 3: Check notification gate

Read the shared runtime state to determine whether chat notification should be sent:

```
HARNESS_STATE = $WORKSPACE_ROOT/runtime/harness-state.json
```

Read `memoryReconciler.reporting.sendReport` from the file.

**Rules:**
- If `harness-state.json` is missing → default `sendReport` to `false`
- If `harness-state.json` is unreadable or malformed → default `sendReport` to `false`
- If `memoryReconciler.reporting` field is absent → default `sendReport` to `false`
- If `sendReport` is `false` → skip chat notification, end run normally
- If `sendReport` is `true` → proceed with notification (Step 4)

**Never fail the run** solely because the reporting state is absent or malformed.

---

## Step 4: Notify (only if sendReport is true)

### On success:

```
Wiki reconciliation complete

Sources: {comma-separated list of found sources}
Ingested: {N} sources, {N} episodes
Compile: {status}
Lint: {status}
```

### On skip:

```
Wiki reconciliation skipped — no sources present
```

### On error:

```
Wiki reconciliation error: {error message}
Ingested before error: {N} sources, {N} episodes
```

---

## Anti-patterns — Do NOT

- Do NOT run `wiki apply` or `wiki_apply`
- Do NOT modify any of the four source files
- Do NOT create MEMORY.md, LTMEMORY.md, PROCEDURES.md, or episode files
- Do NOT consolidate, score, or gate entries
- Do NOT assume hardcoded paths
- Do NOT skip telemetry regardless of notification gate
- Do NOT fail the run because harness-state.json is missing or malformed
