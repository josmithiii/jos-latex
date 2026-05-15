#!/usr/bin/env python3
"""
test-html.py - Scan latex2html+MathJax HTML for known problem signatures.

Currently detects text-mode environments wrapped inside MathJax math
delimiters.  Symptom in the browser:

    \\begin is only supported in math mode

shown by MathJax in red when it tries to parse e.g.

    <SPAN CLASS="MATH">\\(\\fbox{ \\begin{tabular}...\\end{tabular} }\\)</SPAN>

This typically happens when an l2hconf `process_commands_in_tex` registration
for a text-mode command (`\\fbox`, `\\framebox`, ...) preempts a user-supplied
`do_cmd_*` handler -- see jos-latex/l2h-mathjax-init.pl for the fix pattern.

Usage:
    python3 test-html.py --dir HTMLDIR [--verbose]

Exit status: 0 if clean, 1 if any problems found or HTMLDIR is missing.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Environments that MathJax cannot parse inside math delimiters.  A
# `\begin{X}` for any of these inside a <SPAN CLASS="MATH"> or
# <DIV CLASS="MATHDISPLAY"> block is a latex2html-pipeline bug.
FORBIDDEN_IN_MATH: frozenset[str] = frozenset([
    "tabular", "tabular*", "tabularx", "tabulary", "longtable",
    "minipage", "parbox",
    "center", "flushleft", "flushright",
    "itemize", "enumerate", "description", "list",
    "verbatim", "verbatim*", "Verbatim", "lstlisting",
    "figure", "figure*", "table", "table*", "wrapfigure",
    "quote", "quotation", "verse",
    "thebibliography",
])

# A math block is either <SPAN CLASS="MATH">...</SPAN> (inline) or
# <DIV CLASS="MATHDISPLAY">...</DIV> (display).  Bodies can span many lines.
MATH_BLOCK_RE = re.compile(
    r'<SPAN\s+CLASS="MATH">(?P<inline>.*?)</SPAN>'
    r'|<DIV\s+CLASS="MATHDISPLAY">(?P<display>.*?)</DIV>',
    re.DOTALL | re.IGNORECASE,
)

BEGIN_RE = re.compile(r'\\begin\s*\{([A-Za-z][A-Za-z*]*)\}')


def line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_file(path: Path) -> list[tuple[int, str, str, str]]:
    """Return [(line, env, kind, context), ...] for any problems found."""
    text = path.read_text(errors="replace")
    issues: list[tuple[int, str, str, str]] = []
    for m in MATH_BLOCK_RE.finditer(text):
        if m.group("inline") is not None:
            body, body_start, kind = m.group("inline"), m.start("inline"), "inline"
        else:
            body, body_start, kind = m.group("display"), m.start("display"), "display"
        for bm in BEGIN_RE.finditer(body):
            env = bm.group(1)
            if env in FORBIDDEN_IN_MATH:
                file_off = body_start + bm.start()
                context = body[max(0, bm.start() - 20): bm.end() + 20].replace("\n", " ")
                issues.append((line_of_offset(text, file_off), env, kind, context))
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Scan latex2html+MathJax HTML for math-mode escape bugs."
    )
    ap.add_argument("--dir", required=True, help="HTML directory to scan")
    ap.add_argument("--verbose", action="store_true",
                    help="Print per-file status, not just problems")
    args = ap.parse_args()

    root = Path(args.dir)
    if not root.is_dir():
        print(f"*** test-html: not a directory: {root}", file=sys.stderr)
        return 1

    files = sorted(root.glob("*.html"))
    if not files:
        print(f"*** test-html: no *.html files in {root}", file=sys.stderr)
        return 1

    total_issues = 0
    bad_files = 0
    for path in files:
        issues = scan_file(path)
        if issues:
            bad_files += 1
        elif args.verbose:
            print(f"  {path.name}: clean")
        for line, env, kind, ctx in issues:
            print(f"{path}:{line}: \\begin{{{env}}} inside {kind} math "
                  f"(MathJax cannot parse): ...{ctx}...")
            total_issues += 1

    if total_issues:
        print(f"\ntest-html: FAIL -- {total_issues} problem(s) in "
              f"{bad_files}/{len(files)} file(s)", file=sys.stderr)
        return 1
    print(f"test-html: OK -- {len(files)} file(s) scanned, no problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
