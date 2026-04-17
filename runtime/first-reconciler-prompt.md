# Memory Reconciler — First-Time Job (Initial Ingestion)

First reconciliation job, fired once immediately after install. Runs the same ingest → compile → lint flow as the recurring job, but tagged with `mode: first-reconciliation` in telemetry and reported inline to the operator's current session (not isolated) so the first run is visible live.

---

## Execution Guidlines

- **Execute this workflow directly in the current isolated/cron session.**
- **Do NOT spawn a sub-agent** to perform any step of this job.

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

If any value does not match, **STOP and inform the operator**. Config application is owned by memory-wiki setup and `INSTALL.md` — this prompt only verifies. Do not proceed with a misconfigured wiki; ingesting into a non-isolated or bridged vault could leak curated memory outside the intended boundary.

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

## Step 1: Run first reconciliation [SCRIPT]

```bash
python3 $SCRIPTS_DIR/reconcile.py --workspace $WORKSPACE_ROOT
```

Read the JSON output. Record:

- `status` — `"ok"`, `"skipped"`, or `"error"`
- `sources_found` — list of discovered source files
- `sources_ingested` — count of successfully ingested root sources
- `episodes_found` — count of episode files found
- `episodes_ingested` — count of episode files successfully ingested
- `compile.status` — compile result
- `lint.status` — lint result
- `ingest_errors` — list of any ingest failures (partial failures are ok)
- `error` — error message if overall status is `"error"`

---

## Step 2: Append telemetry [SCRIPT]

Always write telemetry regardless of run outcome.

### On success (`status == "ok"`):

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status ok \
  --event run_completed \
  --mode first-reconciliation \
  --details-json '{"sources_found": <list>, "sources_ingested": <N>, "episodes_found": <N>, "episodes_ingested": <N>, "compile_status": "<status>", "lint_status": "<status>"}'
```

### On skip (`status == "skipped"`):

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status skipped \
  --event run_skipped \
  --mode first-reconciliation
```

### On error (`status == "error"`):

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status error \
  --event run_failed \
  --mode first-reconciliation \
  --error "<error message from reconcile output>"
```

---

## Step 3: Report results

Since this runs in the operator's current session, reply inline with a summary — do not use chat notification (that is handled by the recurring `reconciler-prompt.md` via the `sendReport` gate).

```
🔖 Memory Reconciler — First-Time Run Complete

⚙️ Wiki Configuration:
    • Vault mode: isolated
    • Bridge: disabled
    • URL ingest: disabled

📖 Sources found:
    • MEMORY.md: {present/absent}
    • LTMEMORY.md: {present/absent}
    • PROCEDURES.md: {present/absent}
    • Episodes: {count} files

🔧 Reconciliation:
    • Sources ingested: {N}
    • Episodes ingested: {N}

🛠️ Compile: {status}

🔍 Lint: {status}

📅 Next step:
    • memory-reconciler scheduled at Wednesday 23:00, Sunday 23:00
    • Memory reconciliation will run automatically on schedule.
```

Populate `⚙️ Wiki Configuration` from the values read in the guardrail verification step.

## Safety Rules
- Never delete files and directories MEMORY.md, LTMEMORY.md, PROCEDURES.md, memory/, memory/episodes/ and memory/episodes/*.md 
- Never ingest raw daily notes (`memory/YYYY-MM-DD.md`)
- Never ingest dream reports (`DREAMS.md`)
- Never mutate source files — ingestion is read-only
- Never run wiki apply or `wiki_apply`
- Never consolidate score or gate entries
- Never create source files
