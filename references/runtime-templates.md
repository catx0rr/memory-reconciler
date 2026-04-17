# Runtime Templates — Memory Reconciler v1.0.0

Defines the runtime artifacts, schemas, paths, and initialization model for the memory-reconciler. Runtime prompts say how the run behaves. This document defines what the run produces.

---

## Path Model

### Resolution Rules

All paths are resolved dynamically at runtime. No hardcoded absolute paths in execution logic.

| Root | Resolution | Purpose |
|------|-----------|---------|
| `SKILL_ROOT` | Parent of `runtime/` (resolved by the prompt at execution time) | Installed skill location |
| `WORKSPACE_ROOT` | Current working directory | Live workspace with memory files |
| `TELEMETRY_ROOT` | Resolution ladder (see below) | Observability output |
| `SCRIPTS_DIR` | `$SKILL_ROOT/scripts` | Derived from SKILL_ROOT |

### Telemetry Root Resolution Ladder

```
1. Explicit CLI flag (--telemetry-dir)
2. RECONCILER_TELEMETRY_ROOT env var
3. MEMORY_TELEMETRY_ROOT env var
4. ~/.openclaw/telemetry fallback
```

### Workspace vs Telemetry Separation

| Plane | Root | Contains |
|-------|------|----------|
| **Workspace runtime** | `<workspace>/` | MEMORY.md, LTMEMORY.md, PROCEDURES.md, memory/episodes/, runtime/memory-reconciler-metadata.json |
| **Observability** | `<telemetry-root>/` | memory-log-YYYY-MM-DD.jsonl (machine-readable, append-only) |

These are separate planes. Do not store telemetry in the workspace. Do not store live memory state in the telemetry root.

### Timestamp Discipline

| Field | Rule |
|-------|------|
| `timestamp` | Local timezone-aware ISO 8601 with numeric offset — primary for human-facing use |
| `timestamp_utc` | UTC ISO 8601 with Z suffix — companion for machine correlation |

---

## Runtime Metadata

### Target

```
$WORKSPACE_ROOT/runtime/memory-reconciler-metadata.json
```

Package-owned runtime state. Updated after every reconciliation run. Does not contain source memories — only operational metadata.

### Schema

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

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Schema version |
| `lastRun` | string\|null | Local-aware ISO 8601 timestamp of last run |
| `lastRunUtc` | string\|null | UTC ISO 8601 timestamp of last run |
| `lastStatus` | string\|null | Last run outcome: `"ok"`, `"error"`, `"skipped"` |
| `sourcesFound` | string[] | List of source names found (e.g., `["MEMORY.md", "LTMEMORY.md"]`) |
| `sourcesIngested` | int | Count of root sources successfully ingested |
| `episodesIngested` | int | Count of episode files successfully ingested |
| `compileStatus` | string\|null | Last compile outcome: `"ok"`, `"error"` |
| `lintStatus` | string\|null | Last lint outcome: `"ok"`, `"error"` |
| `lastError` | string\|null | Error message from last failed run (null if ok) |

---

## Unified Memory Telemetry Log

### Target

```
TELEMETRY_ROOT/memory-log-YYYY-MM-DD.jsonl
```

One JSON line per reconciliation run. Daily-sharded by local date. Append-only, never modified. Written unconditionally regardless of notification or reporting settings.

Every cron fire produces a telemetry event — including skipped runs where no sources are present. Skipped runs use `event: "run_skipped"` and `status: "skipped"`. A skipped run is a valid outcome, not a failure.

### Writer

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status ok \
  --event run_completed \
  --mode scheduled \
  --agent-id main \
  --details-json '{"sources_found": ["MEMORY.md", "LTMEMORY.md"], "sources_ingested": 2, "episodes_ingested": 5, "compile_status": "ok", "lint_status": "ok"}'
```

On error:

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status error \
  --event run_failed \
  --mode scheduled \
  --error "wiki compile failed with exit code 1"
```

On skip (no sources present):

```bash
python3 $SCRIPTS_DIR/append_memory_log.py \
  --telemetry-dir $TELEMETRY_ROOT \
  --status skipped \
  --event run_skipped \
  --mode scheduled
```

### Event Schema

```json
{
  "timestamp": "2026-04-16T23:00:00+08:00",
  "timestamp_utc": "2026-04-16T15:00:00Z",
  "domain": "memory",
  "component": "memory-reconciler",
  "event": "run_completed",
  "run_id": "recon-2026-04-17T04-40-00-abc123",
  "status": "ok",
  "agent": "main",
  "mode": "scheduled",
  "details": {
    "sources_found": ["MEMORY.md", "LTMEMORY.md", "PROCEDURES.md"],
    "sources_ingested": 3,
    "episodes_found": 5,
    "episodes_ingested": 5,
    "compile_status": "ok",
    "lint_status": "ok"
  }
}
```

### Event Types

| Event | Status | When |
|-------|--------|------|
| `run_started` | `"ok"` | Beginning of reconciliation (optional, for long runs) |
| `run_completed` | `"ok"` | Successful reconciliation with at least one source |
| `run_failed` | `"error"` | Reconciliation encountered a fatal error |
| `run_skipped` | `"skipped"` | All four source groups absent — nothing to do |

---

## Shared Runtime State

### Target

```
$WORKSPACE_ROOT/runtime/memory-state.json
```

Shared across all packages. The memory-reconciler uses the `memoryReconciler` namespace.

### Namespace Schema

Default at initialization — `sendReport: true` so the Memory Reconciler report is delivered back to the operator via the last-used channel:

```json
{
  "memoryReconciler": {
    "reporting": {
      "sendReport": true,
      "delivery": {
        "channel": "last",
        "to": null
      }
    }
  }
}
```

### Merge Rules

- **Create** if file missing — initialize with the `memoryReconciler` namespace (defaults above)
- **Merge** if file exists but `memoryReconciler` key absent — add the namespace with the defaults above
- **Skip** if `memoryReconciler` key already present — do not overwrite existing values
- **Preserve** all other namespaces unconditionally
- Never use `cat >` to overwrite this shared file

### Notification Gate

The `memoryReconciler.reporting.sendReport` field controls chat notification eligibility at runtime:

- `true` (init default) → send notification after successful run
- `false` → skip chat notification, end run silently

**Fail-closed read defaults:** If `memory-state.json` is missing, unreadable, or malformed at read time, treat `sendReport` as `false` for that run. This is a read-time safety guard, not the init default. Never fail a run solely because the reporting state is absent or malformed.

---

## Initialization Model

At install time, the following artifacts are created:

| Artifact | Created By | Notes |
|----------|-----------|-------|
| `runtime/memory-reconciler-metadata.json` | `install.sh` or `INSTALL.md` Step 4 | Empty metadata with null fields |
| `memory-state.json` (memoryReconciler namespace) | `install.sh` or `INSTALL.md` Step 4 | Merge-not-overwrite |
| Wiki isolated vault config | `INSTALL.md` Step 3 / `first-reconciler-prompt.md` Step 2 | Applied via `openclaw config set` |

The four source files (MEMORY.md, LTMEMORY.md, PROCEDURES.md, episodes) are **never created** by this package. They are consumed if present.
