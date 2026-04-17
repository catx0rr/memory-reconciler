# Memory Reconciler — Installation and Setup Guide

Single authoritative guide for installing, configuring, and bootstrapping the memory-reconciler. This is the agent-facing setup authority.

---

## Before Installing

Agent pre-install gate — complete every bullet before touching Step 1:

- Read this entire document first; do not start installing immediately.
- Give the operator a 2-line description of what memory-reconciler does and why they'd want it.
- Check the operator's current config and warn them of anything that will change, conflict, or break (existing cron, existing namespace, non-isolated wiki, shared `memory-state.json`, timezone, etc.).
- Summarize what will be installed as a short bulleted list (skill clone, runtime files, cron job, first run).
- Ask the operator for explicit approval before executing INSTALL.md; do not proceed until they say yes.
- If the runtime directories, files are present, review them if they align with the installation

---

## Path Terminology

| Variable | Meaning |
|----------|---------|
| `SKILLS_PATH` | Parent directory containing all installed skills |
| `SKILL_ROOT` | The memory-reconciler repo directory itself: `$SKILLS_PATH/memory-reconciler` |
| `SKILL.md` | Located at `$SKILL_ROOT/SKILL.md` — the manual-use skill file |
| `WORKSPACE_ROOT` | The active workspace root (current working directory) |

---

## Prerequisites

- Python 3.9+
- Git
- OpenClaw installed with a workspace
- **memory-wiki** installed, enabled, and configured for isolated vault mode — see `$SKILL_ROOT/references/config-template.md` for the required field values and the `openclaw config set` commands. Wiki config application is not owned by this package; memory-reconciler only verifies the config at runtime.

---

## Step 1: Verify Installation

If the operator ran `install.sh`, memory-reconciler is already cloned and the workspace topology is initialized. Verify:

```bash
ls "$SKILL_ROOT/SKILL.md"
```

If the skill is not installed, the operator should run `install.sh` first (see README.md).

### Manual clone (if install.sh was not used)

```bash
export SKILL_PARENT="$HOME/.openclaw/workspace/skills"
export SKILL_ROOT="$SKILL_PARENT/memory-reconciler"
mkdir -p "$SKILL_PARENT"
git clone https://github.com/catx0rr/memory-reconciler.git "$SKILL_ROOT"
```

---

## Step 2: Register `extraDirs` (if needed)

Skip this step if you installed into the default workspace skill root.

```bash
openclaw config set skills.load.extraDirs "[
  \"$SKILL_PARENT\"
]" --strict-json
```

---

## Step 3: Initialize Directories and Files

If the operator ran `install.sh`, directories and runtime files may already exist. Only create what is missing.

Working Directory: the active workspace root.

```bash
mkdir -p runtime
```

### Initialize Runtime Metadata

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

### Initialize Shared Runtime State

Ensure `$WORKSPACE_ROOT/runtime/memory-state.json` exists and contains the `memoryReconciler` reporting namespace. This is a shared file — do not overwrite it. Merge the namespace if the file already exists.

**Default reporting is enabled.** When initializing the `memoryReconciler` reporting namespace, `sendReport` is set to `true` so that the Memory Reconciler report is sent back to the operator via the last-used channel. This is intentional — the reconciler's output (compile/lint results, contradiction dashboards) is the operator's primary signal that hygiene is running. The operator can disable it later by flipping `sendReport` to `false`.

If `$WORKSPACE_ROOT/runtime/memory-state.json` does not exist, create it with:

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

If `$WORKSPACE_ROOT/runtime/memory-state.json` already exists but does not contain a `memoryReconciler` key, merge the `memoryReconciler` namespace (with the defaults above) into the existing file. Preserve all other namespaces unconditionally. Do not use `cat >` to overwrite.

If the `memoryReconciler` key already exists, **skip** — do not overwrite existing reporting state or operator routing. An operator who has already configured `sendReport`, `delivery.channel`, or `delivery.to` keeps their values.

---

## Step 4: Verify Wiki Tools

Verify the required wiki commands are available:

```bash
openclaw wiki ingest --help
openclaw wiki compile --help
openclaw wiki lint --help
```

All three must be available. If any command is missing, memory-wiki may need to be updated.

### Step 4a: Initialize Wiki Vault

Initialize the wiki vault to ensure storage is ready:

```bash
openclaw wiki init
```

---

## Step 5: Resolve Skill Path

Before creating the cron, resolve the actual installed path of the memory-reconciler skill so the cron payload uses an absolute path — not a hardcoded relative one.

### 5a. Try standard skill roots first

```bash
for root in \
  "$HOME/.openclaw/workspace/skills" \
  "$HOME/.openclaw/workspace/.agents/skills" \
  "$HOME/.agents/skills" \
  "$HOME/.openclaw/skills"
do
  if [ -f "$root/memory-reconciler/runtime/reconciler-prompt.md" ]; then
    export SKILL_ROOT="$root/memory-reconciler"
    break
  fi
done
```

### 5b. If not found, check configured `extraDirs`

```bash
if [ -z "${SKILL_ROOT:-}" ]; then
  for root in $(openclaw config get skills.load.extraDirs --json 2>/dev/null | python3 -c "import json,sys; [print(d) for d in json.load(sys.stdin)]" 2>/dev/null); do
    if [ -f "$root/memory-reconciler/runtime/reconciler-prompt.md" ]; then
      export SKILL_ROOT="$root/memory-reconciler"
      break
    fi
  done
fi
```

### 5c. Fail if still unresolved

```bash
if [ -z "${SKILL_ROOT:-}" ] || [ ! -f "$SKILL_ROOT/runtime/reconciler-prompt.md" ]; then
  echo "Could not locate memory-reconciler skill directory."
  echo "Install the skill first or ensure skills.load.extraDirs includes its parent root."
  exit 1
fi

echo "Using SKILL_ROOT=$SKILL_ROOT"
```

---

## Step 6: Create Cron Job

Runs 2x weekly — Wednesday 23:00 and Sunday 23:00 (`0 23 * * 3,0`). The reconciler is a heavier batch job (ingest → compile → lint) and does not need near-real-time freshness.

Use the resolved `$SKILL_ROOT` to construct the absolute path in the cron message:

```
name: "memory-reconciler"
schedule: { kind: "cron", expr: "0 23 * * 3,0", tz: "IANA timezone from system" }
payload: {
  kind: "agentTurn",
  message: "Run memory reconciliation.\n\nRead <RESOLVED_SKILL_ROOT>/runtime/reconciler-prompt.md and follow every step strictly.\n\nWorking directory: <RESOLVED_WORKSPACE_PATH>",
  timeoutSeconds: 1200,
  
}
sessionTarget: "isolated"
delivery: { mode: "announce", channel: <last channel the operator used>, to: <the operator specific id of last channel used> }
```

Replace `<RESOLVED_SKILL_ROOT>` and `<RESOLVED_WORKSPACE_PATH>` with fully resolved absolute paths. No `~`, no `$HOME`, no placeholders in the created cron payload.

Check for existing job first: `openclaw cron list --json`. If `memory-reconciler` already exists, skip.

---

## Step 7: Run First Reconciliation

After setup is complete, DO NOT wait for the cron schedule. Run the first reconciliation immediately:

1. Read `runtime/first-reconciler-prompt.md`
2. Execute every step in the current session (not isolated — the operator should see it happen)
3. The first reconciliation ingests all present sources and initializes the wiki vault

---

## Prompt Ownership

After setup, two prompts govern runtime behavior:

| Prompt | Role | When |
|--------|------|------|
| `runtime/first-reconciler-prompt.md` | One-time bootstrap | Run once during initial setup (Step 7) |
| `runtime/reconciler-prompt.md` | Recurring cron executor | Fired by cron 2x weekly after setup |

The cron job always points to `runtime/reconciler-prompt.md`. The first-reconciler prompt is a one-time run.

---

## Step 8: Verify

- [ ] memory-wiki is installed and enabled
- [ ] Wiki config is set to isolated vault mode (`vaultMode: "isolated"`)
- [ ] Wiki vault initialized (`openclaw wiki init`)
- [ ] Cron job `memory-reconciler` created and enabled
- [ ] `runtime/memory-reconciler-metadata.json` exists
- [ ] `runtime/memory-state.json` contains `memoryReconciler` namespace
- [ ] First reconciliation has run successfully
- [ ] Scripts compile: `python3 -m py_compile $SKILL_ROOT/scripts/reconcile.py`
- [ ] Scripts compile: `python3 -m py_compile $SKILL_ROOT/scripts/status.py`
- [ ] Scripts compile: `python3 -m py_compile $SKILL_ROOT/scripts/append_memory_log.py`

---

## Boundary Statement

memory-reconciler reads from:
- `MEMORY.md` — active durable memory (owned by memory-core)
- `LTMEMORY.md` — reflective long-horizon memory (owned by Reflections)
- `PROCEDURES.md` — procedural memory (owned by Reflections)
- `memory/episodes/*.md` — episodic narratives (owned by Reflections)

memory-reconciler writes to:
- Wiki vault — compiled provenance-bearing wiki content
- `runtime/memory-reconciler-metadata.json` — operational metadata
- `TELEMETRY_ROOT/memory-log-YYYY-MM-DD.jsonl` — unified machine telemetry

memory-reconciler does not own:
- `MEMORY.md` (owned by memory-core)
- `LTMEMORY.md`, `PROCEDURES.md`, `memory/episodes/` (owned by Reflections)
- Active recall, promotion, or dreaming (owned by the host memory pipeline)
- Wiki application / writeback (`wiki_apply` is never called)

---

## Step 9: Cleanup

Remove non-runtime files from the installed skill directory:
- [ ] `.git`
- [ ] `LICENSE`
- [ ] `README.md`

---

## Important Notes

- The install location of the skill is **operator-chosen**
- Prompts **discover the skill location dynamically** at runtime
- No external dependencies beyond Python 3.9+ and OpenClaw with memory-wiki
- Wiki config application is a prerequisite handled outside this install (by memory-wiki setup). This package only **verifies** the config at runtime — it does not apply it.
- `references/config-template.md` documents the expected config shape for operator verification reference
- Telemetry surfaces are defined in `references/runtime-templates.md`
