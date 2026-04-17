# Memory Reconciler v1.0.0

Scheduled cron reconciler that feeds consolidated durable memory into memory-wiki's isolated vault. Ingests, compiles, and lints — producing provenance-bearing searchable wiki sources.

---

## The Problem

Multiple packages produce durable memory surfaces independently. memory-core writes to `MEMORY.md`. Reflections consolidates into `LTMEMORY.md`, `PROCEDURES.md`, and episodic narratives. These surfaces can contain overlapping, contradictory, or drifting information — but without a compiled layer, contradictions remain invisible and no unified search exists across them.

## What This Package Is

memory-reconciler is a scheduled cron reconciler. It reads the four durable memory sources on a timer, feeds them into memory-wiki's isolated vault, and runs one compile and one lint pass. It produces compiled wiki pages with backlinks, contradiction reports, freshness dashboards, and open-question surfaces.

It is not a consolidator. It is not a scoring or gating system. It does not write back to source files. It does not run `wiki_apply`.

## What It Ingests

| Source | Path | Owner |
|--------|------|-------|
| Active durable memory | `MEMORY.md` | memory-core (builtin) |
| Reflective long-horizon memory | `LTMEMORY.md` | Reflections |
| Procedural memory | `PROCEDURES.md` | Reflections |
| Episodic narratives | `memory/episodes/*.md` | Reflections |

These are the only inputs. Daily notes, dream reports, runtime metadata, and URLs are excluded.

## What It Produces

- **Compiled wiki pages** — provenance-bearing searchable content from all four sources
- **Backlinks** — cross-reference links between related wiki entries
- **Dashboards** — contradiction, freshness, and open-question reports
- **Lint results** — quality and consistency warnings
- **Runtime metadata** — `runtime/memory-reconciler-metadata.json` with run state
- **Unified telemetry** — structured events to `memory-log-YYYY-MM-DD.jsonl`

## What It Does NOT Do

| Non-goal | Reason |
|----------|--------|
| Create source files | MEMORY.md, LTMEMORY.md, etc. are owned by other packages |
| Consolidate or score | That is Reflections' job |
| Run `wiki_apply` | No writeback to source files — compiled output stays in the wiki vault |
| Modify source files | Ingestion is strictly read-only |
| Ingest daily notes | Raw daily notes are Reflections' input, not the reconciler's |

## Schedule

Default: Wednesday 23:00 and Sunday 23:00 (`0 23 * * 3,0`).

The reconciler is a heavier batch job (wiki ingest → compile → lint) focused on provenance and contradiction hygiene for the curated seam. It does not need near-real-time freshness, so 2x weekly is the default cadence.

The reconciler assumes consolidated durable memory surfaces already exist when it runs. It does not depend on a specific upstream schedule — it ingests whatever is present at run time.

## Install

### Option 1: Quick Install (operator)

```bash
curl -fsSL https://raw.githubusercontent.com/catx0rr/memory-reconciler/main/install.sh | bash
```

Override defaults if needed:

```bash
CONFIG_ROOT="$HOME/.openclaw" \
WORKSPACE="$HOME/.openclaw/workspace" \
SKILLS_PATH="$HOME/.openclaw/workspace/skills" \
curl -fsSL https://raw.githubusercontent.com/catx0rr/memory-reconciler/main/install.sh | bash
```

### Option 2: Agent Setup

Tell your agent to read `INSTALL.md`:

> Install the memory-reconciler, read the `INSTALL.md` follow every step and provide summary of changes after the install.

## Reference Documentation

| Document | Audience | Content |
|----------|----------|---------|
| `INSTALL.md` | Agent | Setup, wiki configuration, cron wiring, first-run bootstrap |
| `SKILL.md` | Agent | Manual-use skill — operator-triggered reconciliation |
| `references/source-contract.md` | Agent/operator | Four-source seam definition, exclusion list, non-goals |
| `references/config-template.md` | Agent/operator | Wiki isolated vault config shape, `openclaw config set` commands |
| `references/runtime-templates.md` | Agent/operator | Telemetry schema, metadata format, path model, memory-state namespace |
