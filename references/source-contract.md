# Source Contract — Memory Reconciler

Defines the exact sources the memory-reconciler ingests and the discovery order. This is the authoritative seam definition — runtime prompts and scripts must follow it.

---

## Four-Source Seam

The memory-reconciler ingests exactly four source types, in this discovery order:

| Order | Source | Path Pattern | Owner |
|-------|--------|--------------|-------|
| 1 | Active durable memory | `MEMORY.md` | memory-core (builtin) |
| 2 | Reflective long-horizon memory | `LTMEMORY.md` | Reflections |
| 3 | Procedural memory | `PROCEDURES.md` | Reflections |
| 4 | Episodic narratives | `memory/episodes/*.md` (sorted lexicographically) | Reflections |

All paths are relative to `WORKSPACE_ROOT`.

---

## Discovery Rules

- Sources are checked in the order listed above
- Missing sources are **skipped cleanly** — not errors
- Episodes are glob-matched (`memory/episodes/*.md`) and sorted alphabetically for deterministic ingest order
- If **all four source groups are absent**, the run returns a clean `"skipped"` result — not a failure
- Each source is ingested as a whole file — no partial extraction or parsing

---

## Exclusion List

The following are **not ingested** by default:

| Excluded Source | Reason |
|-----------------|--------|
| `memory/YYYY-MM-DD.md` | Raw daily notes — owned by Reflections consolidator |
| `DREAMS.md` | Dream reports — not part of the reconciled seam |
| `memory/.reflections-log.md` | Consolidation cycle reports — Reflections internal |
| `memory/.reflections-archive.md` | Archived entries — Reflections internal |
| Runtime metadata/logs | Package operational state, not memory content |
| Raw `memory/` trees | Unstructured content outside the four sources |
| Arbitrary URLs | URL ingestion is disabled in isolated vault mode |

---

## Non-Goals

This contract defines what the reconciler **consumes**. It does not:

- **Create** any of the four source files — they are owned by memory-core and Reflections
- **Modify** any of the four source files — ingestion is read-only
- **Consolidate** or **score** entries — that is Reflections' job
- **Gate** or **filter** content — all content in the four sources is ingested as-is
- **Run wiki_apply** — compiled wiki output is never written back to source files
