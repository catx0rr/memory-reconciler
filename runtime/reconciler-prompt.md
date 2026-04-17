# Memory Reconciler — Scheduled Reconciliation

Recurring reconciliation job. Fired by cron 2x weekly (Wednesday 23:00, Sunday 23:00). Reconciles the four durable memory sources into the memory-wiki isolated vault: ingest present sources → compile → lint → write telemetry → notify on the configured gate.

---

## Execution Guidlines

- **Execute this workflow directly in the current isolated cron/session context.**
- **Do NOT spawn a sub-agent** to perform Memory Reconciler work.

### Verify Memory-Wiki Configuration Before Proceeding

Before running any step below, verify that memory-wiki is configured for isolated vault mode by reading the current plugin config from `openclaw.json`:

```bash
openclaw config get plugins.entries.memory-wiki.config --json
```

Expected values (must match `$SKILL_ROOT/references/config-template.md`):

| Field | Expected |
|-------|----------|
| `vaultMode` | `"isolated"` |
| `bridge.enabled` | `false` |
| `ingest.allowUrlIngest` | `false` |
| `ingest.autoCompile` | `false` |
| `ingest.maxConcurrentJobs` | `1` |
| `search.backend` | `"local"` |
| `search.corpus` | `"wiki"` |
| `render.createBacklinks` | `true` |
| `render.createDashboards` | `true` |
| `render.preserveHumanBlocks` | `true` |

If any value does not match, **STOP, append a telemetry event with `status: "error"`, and end the run**. Do not proceed with a misconfigured wiki; ingesting into a non-isolated or bridged vault could leak curated memory outside the intended boundary. Config application is owned by memory-wiki setup and `INSTALL.md` — this prompt only verifies.

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
MEMORY_STATE = $WORKSPACE_ROOT/runtime/memory-state.json
```

Read `memoryReconciler.reporting.sendReport` from the file.

**Rules:**
- If `memory-state.json` is missing → default `sendReport` to `false`
- If `memory-state.json` is unreadable or malformed → default `sendReport` to `false`
- If `memoryReconciler.reporting` field is absent → default `sendReport` to `false`
- If `sendReport` is `false` → skip chat notification (still proceed to Step 4 to sync cron)
- If `sendReport` is `true` → proceed to Step 4 to sync cron, then Step 5 to notify

**Never fail the run** solely because the reporting state is absent or malformed.

Also read `memoryReconciler.reporting.delivery.channel` and `memoryReconciler.reporting.delivery.to` — Step 4 uses these to configure the cron route.

---

## Step 4: Sync cron delivery mode

The `sendReport` toggle in `memory-state.json` governs **eligibility**. The cron job's own `--deliver` mode governs **actual delivery**. These must be kept in sync — otherwise the next scheduled run will deliver (or stay silent) against the operator's intent.

Before notifying, read the current cron configuration and update it if it does not match `sendReport`.

### 4.1 Read current cron delivery

```bash
openclaw cron list --json
```

Locate the job named `memory-reconciler`. Inspect its `delivery.mode`, `delivery.channel`, and `delivery.to` fields.

### 4.2 If `sendReport` is `false` — set cron to no-deliver

```bash
openclaw cron edit --name "memory-reconciler" --deliver "none"
```

This ensures no notifications go out on the next scheduled run, matching the operator's disabled state.

**Idempotency:** If the cron is already in `none` mode, skip the edit.

### 4.3 If `sendReport` is `true` — set cron to announce, push channel/target

Resolve the delivery route from `memory-state.json` in this strict order:

1. **Explicit target** — if `delivery.to` is non-null and non-empty, use it as the announce target
2. **Last-route reuse** — if `delivery.channel == "last"` and `delivery.to` is null, reuse the last user route (only if the installed CLI supports it; verify via `openclaw cron --help`)
3. **No valid route** — keep cron in `none` mode and warn clearly; never silently configure `announce` with an unverifiable route

Then edit the cron:

```bash
openclaw cron edit \
  --name "memory-reconciler" \
  --deliver "announce" \
  --channel "<resolved channel>" \
  --to "<resolved target>"
```

**Idempotency:** If the cron is already in `announce` mode with the same `channel` and `to`, skip the edit. Only edit when values differ.

### 4.4 Verify the edit

```bash
openclaw cron list --json
```

Confirm the `memory-reconciler` job's `delivery.mode` (and `channel`, `to` when announce) match the intended state. Never rely on edit success alone.

### 4.5 Non-fatal failures

If the cron edit fails (e.g. CLI missing a flag, permissions issue), **do not fail the run**. Log the failure in telemetry details and continue. The next cron cycle will attempt the sync again.

If `sendReport` is `false`, end the run here — skip Step 5.
If `sendReport` is `true`, proceed to Step 5.

---

## Step 5: Notify (only if sendReport is true)

### On success:

```
🔖 Wiki reconciliation complete

📖 Sources: {bullet type (•) unordered list of found sources}

📥 Ingested: 
    • {N} sources 
    • {N} episodes

🛠️ Compile: {status}

🔍 Lint: {status}

💬 {Let the operator know if anything was missed if none, give insights}
```

### On skip:

```
🔖 Wiki reconciliation skipped — no sources present
```

### On error:

```
🔖 Wiki reconciliation error: {error message}

📥 Ingested before errors: 
    • {N} sources 
    • {N} episodes

💬 {Give short insight about the error}
```

## Safety Rules
- Never delete files and directories MEMORY.md, LTMEMORY.md, PROCEDURES.md, memory/, memory/episodes/ and memory/episodes/*.md 
- Never ingest raw daily notes (`memory/YYYY-MM-DD.md`)
- Never ingest dream reports (`DREAMS.md`)
- Never mutate source files — ingestion is read-only
- Never run wiki apply or `wiki_apply`
- Never consolidate score or gate entries
- Never create source files
