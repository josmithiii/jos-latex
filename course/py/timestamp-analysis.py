#!/usr/bin/env python3
"""
timestamp-analysis.py - Analyze build timestamp files and predict what will rebuild

Usage:
    python timestamp-analysis.py          # Show timestamp analysis
    python timestamp-analysis.py -v       # Verbose: show all dependencies
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Define the dependency chain (target: [dependencies])
# Based on Makefile.tex
DEPENDENCIES = {
    '.LATEX-PASS1-TIMESTAMP': ['*.tex', '*.sty'],  # Source files
    '.LATEX-PASS2-TIMESTAMP': ['.LATEX-PASS1-TIMESTAMP'],
    '.LATEX-PASS3-TIMESTAMP': ['.LATEX-PASS2-TIMESTAMP'],
    '.BIBTEX-TIMESTAMP': ['.LATEX-PASS1-TIMESTAMP'],  # Simplified
    '.HTML-TIMESTAMP': ['.LATEX-PASS1-TIMESTAMP', '.BIBTEX-TIMESTAMP'],
    '.INSTALL-TIMESTAMP': ['.HTML-TIMESTAMP'],
    '.LINK-TIMESTAMP': ['.INSTALL-TIMESTAMP', '.LOCALDICT-TIMESTAMP'],
    '.LOCALDICT-TIMESTAMP': [],  # External dependency
}

# What each timestamp triggers
TRIGGERS = {
    '.LATEX-PASS1-TIMESTAMP': 'LaTeX pass 1',
    '.LATEX-PASS2-TIMESTAMP': 'LaTeX pass 2',
    '.LATEX-PASS3-TIMESTAMP': 'LaTeX pass 3',
    '.BIBTEX-TIMESTAMP': 'BibTeX',
    '.HTML-TIMESTAMP': 'LaTeX2HTML (full HTML rebuild)',
    '.INSTALL-TIMESTAMP': 'Install to DESTROOT',
    '.LINK-TIMESTAMP': 'Link processing',
    '.LOCALDICT-TIMESTAMP': 'Local dictionary',
}

def get_mtime(path: Path) -> float | None:
    """Get modification time of a file, or None if it doesn't exist."""
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return None

def format_time(mtime: float | None) -> str:
    """Format modification time for display."""
    if mtime is None:
        return "MISSING"
    dt = datetime.fromtimestamp(mtime)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def analyze_timestamps(base_dir: Path, verbose: bool = False) -> list[tuple[str, str]]:
    """Analyze timestamps and return list of (target, reason) for what will rebuild."""
    rebuilds = []
    timestamps = {}

    # Collect all timestamp mtimes
    for ts in DEPENDENCIES.keys():
        ts_path = base_dir / ts
        timestamps[ts] = get_mtime(ts_path)

    # Print current state
    print("Timestamp files:")
    print("-" * 60)

    # Sort by mtime for display
    sorted_ts = sorted(timestamps.items(), key=lambda x: x[1] or 0)
    for ts, mtime in sorted_ts:
        status = ""
        if mtime is None:
            status = " [MISSING - will trigger build]"
        print(f"  {ts:30} {format_time(mtime)}{status}")

    print()

    # Check each target's dependencies
    print("Dependency analysis:")
    print("-" * 60)

    for target, deps in DEPENDENCIES.items():
        target_mtime = timestamps.get(target)

        if target_mtime is None:
            rebuilds.append((target, "timestamp missing"))
            print(f"  {target}: MISSING - will rebuild {TRIGGERS.get(target, target)}")
            continue

        # Check timestamp dependencies
        for dep in deps:
            if dep.startswith('.') and dep.endswith('-TIMESTAMP'):
                dep_mtime = timestamps.get(dep)
                if dep_mtime is not None and dep_mtime > target_mtime:
                    reason = f"{dep} is newer"
                    rebuilds.append((target, reason))
                    print(f"  {target}: OUT OF DATE")
                    print(f"      {dep} ({format_time(dep_mtime)}) > {target} ({format_time(target_mtime)})")
                    print(f"      Will rebuild: {TRIGGERS.get(target, target)}")
                    break
        else:
            if verbose:
                print(f"  {target}: up to date")

    return rebuilds

def predict_cascade(rebuilds: list[tuple[str, str]]) -> None:
    """Show what will be rebuilt due to cascade effects."""
    if not rebuilds:
        print("\nAll timestamps up to date. No rebuild needed.")
        return

    print("\nRebuild cascade:")
    print("-" * 60)

    # Find the earliest trigger in the chain
    chain_order = [
        '.LATEX-PASS1-TIMESTAMP',
        '.LATEX-PASS2-TIMESTAMP',
        '.LATEX-PASS3-TIMESTAMP',
        '.BIBTEX-TIMESTAMP',
        '.HTML-TIMESTAMP',
        '.INSTALL-TIMESTAMP',
        '.LINK-TIMESTAMP',
    ]

    rebuild_set = {r[0] for r in rebuilds}
    triggered = set()

    for ts in chain_order:
        if ts in rebuild_set or ts in triggered:
            triggered.add(ts)
            print(f"  -> {TRIGGERS.get(ts, ts)}")
            # Add downstream dependencies
            for downstream, deps in DEPENDENCIES.items():
                if ts in deps:
                    triggered.add(downstream)

def main():
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    base_dir = Path(__file__).parent

    print("=" * 60)
    print("Build Timestamp Analysis")
    print("=" * 60)
    print()

    rebuilds = analyze_timestamps(base_dir, verbose)
    predict_cascade(rebuilds)

    print()
    if rebuilds:
        print("Tip: To skip HTML rebuild, run: touch .HTML-TIMESTAMP .INSTALL-TIMESTAMP .LINK-TIMESTAMP")
        print("Or use: make cw  (quick course + web, skips rebuild check)")

if __name__ == '__main__':
    main()
