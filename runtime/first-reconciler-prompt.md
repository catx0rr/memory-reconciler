# Memory Reconciler — First-Time Job (Initial Ingestion)

First reconciliation job, fired once immediately after install. Runs the same ingest → compile → lint flow as the recurring job, but tagged with `mode: first-reconciliation` in telemetry and reported inline to the operator's current session (not isolated) so the first run is visible live.

---

## Execution Guardrails

### Run Directly, No Delegation

- **Execute this workflow directly in the current session.**
- **Do NOT spawn a sub-agent** to perform any step of this job.
- **Do NOT delegate** source discovery, wiki ingest, compile, lint, telemetry append, or reporting to a sub-agent.
- Sub-agent delegation breaks the isolation guarantees of the current session and can fan out unintended side effects. This job must run end-to-end in the current context.

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

---

## Anti-patterns — Do NOT

- Do NOT spawn a sub-agent or delegate any step — run this workflow directly
- Do NOT create runtime files, directories, or cron jobs from this prompt — setup is owned by `INSTALL.md`
- Do NOT run `openclaw wiki init`, `openclaw cron add`, `openclaw config set`, or any other setup command — setup is owned by `INSTALL.md` / `install.sh`
- Do NOT merge or initialize the `memoryReconciler` namespace in `memory-state.json` — that is done during install
- Do NOT run `wiki apply` or `wiki_apply`
- Do NOT modify any of the four source files (MEMORY.md, LTMEMORY.md, PROCEDURES.md, episodes)
- Do NOT create MEMORY.md, LTMEMORY.md, PROCEDURES.md, or episode files
- Do NOT consolidate, score, or gate entries
- Do NOT assume hardcoded paths — resolve SKILL_ROOT, WORKSPACE_ROOT, TELEMETRY_ROOT dynamically
- Do NOT skip telemetry
