#!/usr/bin/env bash
set -euo pipefail

# Memory Reconciler — Operator Install Script
#
# Installs the memory-reconciler skill and initializes the workspace topology.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/catx0rr/memory-reconciler/main/install.sh | bash
#
# Override defaults:
#   CONFIG_ROOT="$HOME/.openclaw" \
#   WORKSPACE="$HOME/.openclaw/workspace" \
#   SKILLS_PATH="$HOME/.openclaw/workspace/skills" \
#   curl -fsSL https://raw.githubusercontent.com/catx0rr/memory-reconciler/main/install.sh | bash

REPO_URL="https://github.com/catx0rr/memory-reconciler.git"

CONFIG_ROOT="${CONFIG_ROOT:-$HOME/.openclaw}"
WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
SKILLS_PATH="${SKILLS_PATH:-$HOME/.openclaw/workspace/skills}"
SKILL_ROOT="$SKILLS_PATH/memory-reconciler"

echo "Memory Reconciler installer"
echo "---------------------------"
echo "  CONFIG_ROOT:  $CONFIG_ROOT"
echo "  WORKSPACE:    $WORKSPACE"
echo "  SKILLS_PATH:  $SKILLS_PATH"
echo "  SKILL_ROOT:   $SKILL_ROOT"
echo ""

# ── A. Install/update the repo ──────────────────────────────────────

mkdir -p "$SKILLS_PATH"

if [ -d "$SKILL_ROOT/.git" ]; then
    echo "[repo] Existing installation found. Updating..."
    cd "$SKILL_ROOT"
    git pull --ff-only || {
        echo "Warning: fast-forward pull failed. Manual resolution may be needed."
        echo "Location: $SKILL_ROOT"
        exit 1
    }
    echo "[repo] Updated successfully."
elif [ -d "$SKILL_ROOT" ]; then
    echo "Error: Directory exists but is not a git repo: $SKILL_ROOT"
    echo "Remove it manually or choose a different SKILLS_PATH, then re-run."
    exit 1
else
    echo "[repo] Cloning memory-reconciler..."
    git clone "$REPO_URL" "$SKILL_ROOT"
    echo "[repo] Cloned successfully."
fi

if [ ! -f "$SKILL_ROOT/SKILL.md" ]; then
    echo "Error: SKILL.md not found at $SKILL_ROOT/SKILL.md"
    echo "Installation may be incomplete."
    exit 1
fi

# ── B. Initialize workspace topology ────────────────────────────────

echo ""
echo "[init] Initializing workspace topology..."

mkdir -p "$WORKSPACE/runtime"

# Runtime metadata
if [ ! -f "$WORKSPACE/runtime/memory-reconciler-metadata.json" ]; then
    echo "[init] Creating runtime/memory-reconciler-metadata.json"
    cat > "$WORKSPACE/runtime/memory-reconciler-metadata.json" <<'METAEOF'
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
METAEOF
else
    echo "[init] runtime/memory-reconciler-metadata.json already exists — skipping"
fi

# Note: Wiki config is applied via 'openclaw config set' at agent setup time,
# not by this installer. See INSTALL.md Step 3 and references/config-template.md.

# ── C. Initialize shared runtime state ──────────────────────────────

HARNESS="$WORKSPACE/runtime/harness-state.json"

if [ ! -f "$HARNESS" ]; then
    echo "[init] Creating runtime/harness-state.json"
    cat > "$HARNESS" <<'HARNEOF'
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
HARNEOF
elif ! python3 -c "import json,sys; d=json.load(open('$HARNESS')); sys.exit(0 if 'memoryReconciler' in d else 1)" 2>/dev/null; then
    echo "[init] Merging memoryReconciler namespace into existing harness-state.json"
    python3 -c "
import json, sys
with open('$HARNESS', 'r') as f:
    d = json.load(f)
d['memoryReconciler'] = {
    'reporting': {
        'sendReport': False,
        'delivery': {'channel': 'last', 'to': None}
    }
}
with open('$HARNESS', 'w') as f:
    json.dump(d, f, indent=2)
"
else
    echo "[init] harness-state.json already contains memoryReconciler namespace — skipping"
fi

# ── Done ────────────────────────────────────────────────────────────

echo ""
echo "Memory Reconciler installed and initialized."
echo ""
echo "  Skill root:  $SKILL_ROOT"
echo "  SKILL.md:    $SKILL_ROOT/SKILL.md"
echo "  Workspace:   $WORKSPACE"
echo ""
echo "Next step:"
echo "  Tell your agent to read INSTALL.md in the memory-reconciler skill directory."
echo ""
echo "  Example:"
echo "    \"Read INSTALL.md in $SKILL_ROOT and follow every step.\""
echo ""
