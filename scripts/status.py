#!/usr/bin/env python3
"""
memory-reconciler: status — runtime status reader

Reads the runtime metadata file and reports the last run status,
source presence, and operational state.

Usage:
    python3 status.py
    python3 status.py --workspace /path/to/workspace
    python3 status.py --metadata-file /path/to/memory-reconciler-metadata.json
"""

import argparse
import glob
import json
import os
import sys
from pathlib import Path


def _check_source_presence(workspace: str) -> dict:
    """Check which of the four source types are present in the workspace."""
    ws = Path(workspace)
    episodes = sorted(glob.glob(str(ws / 'memory' / 'episodes' / '*.md')))

    return {
        'memory': (ws / 'MEMORY.md').is_file(),
        'ltmemory': (ws / 'LTMEMORY.md').is_file(),
        'procedures': (ws / 'PROCEDURES.md').is_file(),
        'episodes': len(episodes),
    }


def main():
    parser = argparse.ArgumentParser(
        description='Memory Reconciler: Runtime Status Reader'
    )
    parser.add_argument(
        '--metadata-file',
        default='runtime/memory-reconciler-metadata.json',
        help='Path to metadata file (default: runtime/memory-reconciler-metadata.json)'
    )
    parser.add_argument(
        '--workspace',
        default=os.getcwd(),
        help='Workspace root directory (default: current directory)'
    )

    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)

    # Resolve metadata path (relative to workspace if not absolute)
    meta_path = args.metadata_file
    if not os.path.isabs(meta_path):
        meta_path = os.path.join(workspace, meta_path)

    result = {
        'status': 'ok',
        'metadata_file': meta_path,
        'metadata_exists': False,
        'last_run': None,
        'last_run_utc': None,
        'last_status': None,
        'sources_found': None,
        'sources_ingested': None,
        'episodes_ingested': None,
        'compile_status': None,
        'lint_status': None,
        'last_error': None,
        'sources_present': _check_source_presence(workspace),
    }

    # Read metadata if it exists
    if os.path.isfile(meta_path):
        result['metadata_exists'] = True
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)

            result['last_run'] = meta.get('lastRun')
            result['last_run_utc'] = meta.get('lastRunUtc')
            result['last_status'] = meta.get('lastStatus')
            result['sources_found'] = meta.get('sourcesFound', [])
            result['sources_ingested'] = meta.get('sourcesIngested', 0)
            result['episodes_ingested'] = meta.get('episodesIngested', 0)
            result['compile_status'] = meta.get('compileStatus')
            result['lint_status'] = meta.get('lintStatus')
            result['last_error'] = meta.get('lastError')

        except (json.JSONDecodeError, OSError) as e:
            result['status'] = 'error'
            result['last_error'] = f'Failed to read metadata: {e}'

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
