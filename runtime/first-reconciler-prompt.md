# Memory Reconciler — First-Time Bootstrap

Run this ONCE immediately after installing memory-reconciler. This prompt sets up the isolated wiki vault, initializes runtime state, creates the cron job, and runs the first reconciliation.

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

## Step 1: Verify memory-wiki is enabled

Check that memory-wiki is installed and available:

```bash
openclaw wiki status
```

If the command fails or memory-wiki is not installed, STOP and inform the operator:

> "memory-wiki is not installed or not enabled. Install memory-wiki before proceeding with memory-reconciler setup."

Do not continue without a working memory-wiki installation.

---

## Step 2: Apply isolated vault mode settings

Apply the isolated vault configuration through OpenClaw's plugin config system. Use the exact values from `$SKILL_ROOT/references/config-template.md`:

```bash
openclaw config set plugins.entries.memory-wiki.config.vaultMode '"isolated"' --strict-json
openclaw config set plugins.entries.memory-wiki.config.bridge.enabled 'false' --strict-json
openclaw config set plugins.entries.memory-wiki.config.ingest.allowUrlIngest 'false' --strict-json
openclaw config set plugins.entries.memory-wiki.config.ingest.autoCompile 'false' --strict-json
openclaw config set plugins.entries.memory-wiki.config.ingest.maxConcurrentJobs '1' --strict-json
openclaw config set plugins.entries.memory-wiki.config.search.backend '"local"' --strict-json
openclaw config set plugins.entries.memory-wiki.config.search.corpus '"wiki"' --strict-json
openclaw config set plugins.entries.memory-wiki.config.render.createBacklinks 'true' --strict-json
openclaw config set plugins.entries.memory-wiki.config.render.createDashboards 'true' --strict-json
openclaw config set plugins.entries.memory-wiki.config.render.preserveHumanBlocks 'true' --strict-json
```

### Verify applied config

```bash
openclaw config get plugins.entries.memory-wiki.config --json
```

Compare the output against `$SKILL_ROOT/references/config-template.md`. All fields must match:
- `vaultMode` = `"isolated"`
- `bridge.enabled` = `false`
- `ingest.allowUrlIngest` = `false`
- `ingest.autoCompile` = `false`
- `ingest.maxConcurrentJobs` = `1`
- `search.backend` = `"local"`
- `search.corpus` = `"wiki"`
- `render.createBacklinks` = `true`
- `render.createDashboards` = `true`
- `render.preserveHumanBlocks` = `true`

If any field does not match, re-apply and verify again.

---

## Step 3: Initialize runtime metadata

Create `$WORKSPACE_ROOT/runtime/memory-reconciler-metadata.json` if it does not exist:

```json
{
  "version": "1.0.0",
  "lastRun": null,
  "lastRunUtc": null,
  "lastStatus": null,
  "sourcesFound": [],
  "sourcesIngested": 0,
  "episodesIngested": 0,
  "compileStatus": null,
  "lintStatus": null,
  "lastError": null
}
```

If the file already exists, skip — do not overwrite.

---

## Step 4: Merge memoryReconciler namespace into harness-state.json

Read `$WORKSPACE_ROOT/runtime/harness-state.json`.

**If the file does not exist**, create it:

```json
{
  "memoryReconciler": {
    "reporting": {
      "sendReport": false,
      "delivery": {
        "channel": "last",
        "to": null
      }
    }
  }
}
```

**If the file exists but does not contain a `memoryReconciler` key**, merge the namespace:

```python
import json
with open(harness_path, 'r') as f:
    data = json.load(f)
data['memoryReconciler'] = {
    'reporting': {
        'sendReport': False,
        'delivery': {'channel': 'last', 'to': None}
    }
}
with open(harness_path, 'w') as f:
    json.dump(data, f, indent=2)
```

**If the `memoryReconciler` key already exists**, skip — do not overwrite existing reporting state.

**Preserve all other namespaces unconditionally.** Never use `cat >` to overwrite this shared file.

---

## Step 5: Verify four-source seam

Check the existence of each source in the workspace:

| Source | Path | Present? |
|--------|------|----------|
| Active durable memory | `$WORKSPACE_ROOT/MEMORY.md` | |
| Reflective memory | `$WORKSPACE_ROOT/LTMEMORY.md` | |
| Procedural memory | `$WORKSPACE_ROOT/PROCEDURES.md` | |
| Episodes | `$WORKSPACE_ROOT/memory/episodes/*.md` | (count) |

Report which sources are present. Missing sources are **not errors** — they may appear later as other packages run. The reconciler will skip missing sources cleanly at runtime.

---

## Step 6: Create cron job

Create the recurring cron job. Check for an existing job first (idempotency):

```bash
openclaw cron list --json
```

If a job named `memory-reconciler` already exists, skip creation.

Otherwise, create:

```bash
openclaw cron add \
  --name "memory-reconciler" \
  --cron "0 23 * * 3,0" \
  --tz "<IANA timezone from system>" \
  --session isolated \
  --no-deliver \
  --timeout-seconds 1200 \
  --message "Run memory reconciliation.\n\nRead <RESOLVED_SKILL_ROOT>/runtime/reconciler-prompt.md and follow every step strictly.\n\nWorking directory: <RESOLVED_WORKSPACE_PATH>"
```

Replace `<RESOLVED_SKILL_ROOT>` and `<RESOLVED_WORKSPACE_PATH>` with fully resolved absolute paths. No `~`, no `$HOME`, no placeholders in the created cron payload.

---

## Step 7: Initialize wiki vault

Initialize the memory-wiki vault before the first reconciliation run:

```bash
openclaw wiki init
```

This ensures the wiki storage is ready to accept ingested content.

---

## Step 8: Run first reconciliation [SCRIPT]

Run the first reconciliation cycle:

```bash
python3 $SCRIPTS_DIR/reconcile.py --workspace $WORKSPACE_ROOT
```

Read the JSON output. Record:
- `status` — ok, skipped, or error
- `sources_found` — which sources were present
- `sources_ingested` — how many were successfully ingested
- `episodes_ingested` — how many episode files were ingested
- `compile.status` — compile result
- `lint.status` — lint result

---

## Step 9: Append telemetry [SCRIPT]

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status <status from step 8> \
  --event <run_completed or run_skipped or run_failed> \
  --mode first-reconciliation \
  --details-json '<JSON summary from step 8>'
```

---

## Step 10: Report results

Compose and reply with a summary:

```
Memory Reconciler — First-Time Bootstrap Complete

Wiki Configuration:
  Vault mode: isolated
  Bridge: disabled
  URL ingest: disabled

Sources found:
  MEMORY.md: {present/absent}
  LTMEMORY.md: {present/absent}
  PROCEDURES.md: {present/absent}
  Episodes: {count} files

Reconciliation:
  Sources ingested: {N}
  Episodes ingested: {N}
  Compile: {status}
  Lint: {status}

Cron: memory-reconciler scheduled at Wednesday 23:00, Sunday 23:00
Next step: reconciliation will run automatically on schedule.
```

---

## Anti-patterns — Do NOT

- Do NOT run `wiki apply` or `wiki_apply`
- Do NOT modify any of the four source files
- Do NOT create MEMORY.md, LTMEMORY.md, PROCEDURES.md, or episode files
- Do NOT consolidate, score, or gate entries
- Do NOT assume hardcoded paths — resolve SKILL_ROOT, WORKSPACE_ROOT, TELEMETRY_ROOT dynamically
- Do NOT skip telemetry even when notification is silent
