#!/usr/bin/env python3
"""
memory-reconciler: reconcile — main reconciliation orchestrator

Discovers the four durable memory sources, ingests each into memory-wiki,
runs one compile and one lint pass, then writes runtime metadata.

Source discovery order (deterministic):
    1. MEMORY.md
    2. LTMEMORY.md
    3. PROCEDURES.md
    4. memory/episodes/*.md (sorted lexicographically)

Wiki config is managed through OpenClaw's plugin config system
(plugins.entries.memory-wiki.config), not through a package-local file.

Usage:
    python3 reconcile.py
    python3 reconcile.py --workspace /path/to/workspace
    python3 reconcile.py --dry-run
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ── Source contract ─────────────────────────────────────────────────

ROOT_SOURCES = ['MEMORY.md', 'LTMEMORY.md', 'PROCEDURES.md']
EPISODES_GLOB = 'memory/episodes/*.md'


def _timestamp_pair() -> dict:
    """Generate the timestamp pair: local-aware and UTC."""
    now_local = datetime.now().astimezone()
    now_utc = now_local.astimezone(timezone.utc)
    return {
        'timestamp': now_local.isoformat(),
        'timestamp_utc': now_utc.isoformat().replace('+00:00', 'Z'),
    }


# ── Wiki command runner ────────────────────────────────────────────

def _run_wiki_cmd(args: list, timeout: int = 120) -> dict:
    """Run an openclaw wiki subcommand and capture the result."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            'status': 'ok' if result.returncode == 0 else 'error',
            'returncode': result.returncode,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {'status': 'error', 'returncode': -1, 'stdout': '', 'stderr': 'timeout'}
    except FileNotFoundError:
        return {'status': 'error', 'returncode': -1, 'stdout': '', 'stderr': 'openclaw not found in PATH'}


# ── Source discovery ───────────────────────────────────────────────

def discover_sources(workspace: str) -> dict:
    """Discover which of the four source types are present."""
    ws = Path(workspace)

    found_roots = []
    for src in ROOT_SOURCES:
        if (ws / src).is_file():
            found_roots.append(src)

    episodes = sorted(glob.glob(str(ws / EPISODES_GLOB)))

    return {
        'root_sources': found_roots,
        'episodes': episodes,
        'total_found': len(found_roots) + len(episodes),
    }


# ── Ingest ─────────────────────────────────────────────────────────

def ingest_sources(workspace: str, sources: dict, dry_run: bool = False) -> dict:
    """Ingest each discovered source into memory-wiki."""
    ws = Path(workspace)
    ingested = []
    errors = []

    # Ingest root sources in contract order
    for src in sources['root_sources']:
        abs_path = str(ws / src)
        if dry_run:
            ingested.append({'source': src, 'status': 'dry_run'})
            continue

        result = _run_wiki_cmd(['openclaw', 'wiki', 'ingest', abs_path])
        if result['status'] == 'ok':
            ingested.append({'source': src, 'status': 'ok'})
        else:
            errors.append({
                'source': src,
                'error': result.get('stderr', 'unknown error'),
                'returncode': result.get('returncode'),
            })

    # Ingest episodes in sorted order
    for ep_path in sources['episodes']:
        ep_name = os.path.relpath(ep_path, workspace)
        if dry_run:
            ingested.append({'source': ep_name, 'status': 'dry_run'})
            continue

        result = _run_wiki_cmd(['openclaw', 'wiki', 'ingest', ep_path])
        if result['status'] == 'ok':
            ingested.append({'source': ep_name, 'status': 'ok'})
        else:
            errors.append({
                'source': ep_name,
                'error': result.get('stderr', 'unknown error'),
                'returncode': result.get('returncode'),
            })

    ok_or_dry = ('ok', 'dry_run')
    return {
        'ingested': ingested,
        'errors': errors,
        'sources_ingested': len([
            i for i in ingested if i['status'] in ok_or_dry
            and not i['source'].startswith('memory/episodes/')
        ]),
        'episodes_ingested': len([
            i for i in ingested if i['status'] in ok_or_dry
            and i['source'].startswith('memory/episodes/')
        ]),
    }


# ── Compile and lint ───────────────────────────────────────────────

def compile_wiki(dry_run: bool = False) -> dict:
    """Run wiki compile once after all ingests."""
    if dry_run:
        return {'status': 'dry_run', 'output': ''}

    result = _run_wiki_cmd(['openclaw', 'wiki', 'compile'])
    return {
        'status': result['status'],
        'output': result.get('stdout', '') or result.get('stderr', ''),
    }


def lint_wiki(dry_run: bool = False) -> dict:
    """Run wiki lint once after compile."""
    if dry_run:
        return {'status': 'dry_run', 'output': ''}

    result = _run_wiki_cmd(['openclaw', 'wiki', 'lint'])
    return {
        'status': result['status'],
        'output': result.get('stdout', '') or result.get('stderr', ''),
    }


# ── Metadata update ───────────────────────────────────────────────

def update_metadata(metadata_path: str, run_result: dict) -> None:
    """Write the run result to the metadata file."""
    meta_dir = os.path.dirname(metadata_path)
    if meta_dir:
        os.makedirs(meta_dir, exist_ok=True)

    ts = run_result.get('timestamp', _timestamp_pair())

    metadata = {
        'version': '1.0.0',
        'lastRun': ts['timestamp'] if isinstance(ts, dict) else ts,
        'lastRunUtc': ts['timestamp_utc'] if isinstance(ts, dict) else None,
        'lastStatus': run_result.get('status', 'unknown'),
        'sourcesFound': run_result.get('sources_found', []),
        'sourcesIngested': run_result.get('sources_ingested', 0),
        'episodesIngested': run_result.get('episodes_ingested', 0),
        'compileStatus': (run_result.get('compile') or {}).get('status'),
        'lintStatus': (run_result.get('lint') or {}).get('status'),
        'lastError': run_result.get('error'),
    }

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


# ── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Memory Reconciler: Main Reconciliation Orchestrator'
    )
    parser.add_argument(
        '--workspace',
        default=os.getcwd(),
        help='Workspace root directory (default: current directory)'
    )
    parser.add_argument(
        '--metadata-file',
        default='runtime/memory-reconciler-metadata.json',
        help='Path to metadata file (default: runtime/memory-reconciler-metadata.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would happen without calling wiki commands'
    )

    args = parser.parse_args()

    workspace = os.path.abspath(args.workspace)
    start_time = time.monotonic()

    # Resolve metadata path
    meta_path = args.metadata_file
    if not os.path.isabs(meta_path):
        meta_path = os.path.join(workspace, meta_path)

    # Timestamps
    ts = _timestamp_pair()

    # Step 1: Discover sources
    sources = discover_sources(workspace)

    # Short-circuit: all sources absent
    if sources['total_found'] == 0:
        result = {
            'status': 'skipped',
            'reason': 'all_sources_absent',
            'timestamp': ts,
            'sources_found': [],
            'sources_ingested': 0,
            'episodes_found': 0,
            'episodes_ingested': 0,
            'ingest_errors': [],
            'compile': None,
            'lint': None,
            'duration_ms': int((time.monotonic() - start_time) * 1000),
            'dry_run': args.dry_run,
        }

        if not args.dry_run:
            update_metadata(meta_path, result)

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    # Step 2: Ingest sources
    ingest_result = ingest_sources(workspace, sources, dry_run=args.dry_run)

    # Step 3: Compile
    compile_result = compile_wiki(dry_run=args.dry_run)

    # Step 4: Lint
    lint_result = lint_wiki(dry_run=args.dry_run)

    # Determine overall status
    overall_status = 'ok'
    error_msg = None
    if ingest_result['errors']:
        if ingest_result['sources_ingested'] == 0:
            overall_status = 'error'
            error_msg = f"All ingests failed: {ingest_result['errors'][0]['error']}"
        # Partial failures are still 'ok' — some sources were ingested
    if compile_result['status'] == 'error':
        overall_status = 'error'
        error_msg = f"wiki compile failed: {compile_result.get('output', 'unknown')}"
    if lint_result['status'] == 'error' and overall_status != 'error':
        # Lint errors are warnings, not fatal
        pass

    # Build result
    result = {
        'status': overall_status,
        'timestamp': ts,
        'sources_found': sources['root_sources'] + [
            os.path.relpath(ep, workspace) for ep in sources['episodes']
        ],
        'sources_ingested': ingest_result['sources_ingested'],
        'episodes_found': len(sources['episodes']),
        'episodes_ingested': ingest_result['episodes_ingested'],
        'ingest_errors': ingest_result['errors'],
        'compile': compile_result,
        'lint': lint_result,
        'duration_ms': int((time.monotonic() - start_time) * 1000),
        'dry_run': args.dry_run,
    }

    if error_msg:
        result['error'] = error_msg

    # Update metadata (skip on dry run)
    if not args.dry_run:
        update_metadata(meta_path, result)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
