# Wiki Config Template — Memory Reconciler

Defines the exact memory-wiki configuration shape for isolated vault mode.

**Important:** This file is a **reference template**, not the live config source. Wiki config application is a prerequisite handled by memory-wiki setup — **not** by the memory-reconciler package. Memory-reconciler only verifies the config at runtime (see the "Verify Memory-Wiki Configuration" guardrail in both runtime prompts). This file documents the expected shape and provides the `openclaw config set` commands the operator can use to apply it.

---

## Isolated Vault Configuration

```json
{
  "vaultMode": "isolated",
  "bridge": {
    "enabled": false
  },
  "ingest": {
    "allowUrlIngest": false,
    "autoCompile": false,
    "maxConcurrentJobs": 1
  },
  "search": {
    "backend": "local",
    "corpus": "wiki"
  },
  "render": {
    "createBacklinks": true,
    "createDashboards": true,
    "preserveHumanBlocks": true
  }
}
```

---

## Field Rationale

| Field | Value | Reason |
|-------|-------|--------|
| `vaultMode` | `"isolated"` | Wiki operates in its own namespace — no cross-vault leakage |
| `bridge.enabled` | `false` | No bridge to external wikis or public seams |
| `ingest.allowUrlIngest` | `false` | Only local file ingestion — no external URLs |
| `ingest.autoCompile` | `false` | Compile is called explicitly after all ingests complete |
| `ingest.maxConcurrentJobs` | `1` | Sequential ingestion prevents race conditions |
| `search.backend` | `"local"` | Local search only — no external search backends |
| `search.corpus` | `"wiki"` | Search within wiki corpus only |
| `render.createBacklinks` | `true` | Backlinks enable provenance tracking across sources |
| `render.createDashboards` | `true` | Contradiction/freshness/open-question dashboards |
| `render.preserveHumanBlocks` | `true` | Respect human-authored blocks during compilation |

---

## Applying the Configuration

Config application is a **prerequisite** handled by the operator during memory-wiki setup — not by the memory-reconciler package. The operator can use these `openclaw config set` commands to apply the required values:

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

---

## Verification

After applying, verify the config matches this template:

```bash
openclaw config get plugins.entries.memory-wiki.config --json
```

Compare the output against the JSON block above. All fields must match.
