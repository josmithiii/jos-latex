#!/usr/bin/env python3
"""
inject-theme-toggle.py - Inject the dark/light theme toggle into l2h HTML files.

Usage:
    python inject-theme-toggle.py --dest DIR     # Inject into DIR
    python inject-theme-toggle.py --dest DIR --dry-run
    python inject-theme-toggle.py --dest DIR --remove

Injects two tags before </head> in every *.html file under DIR:

    1. An inline script that reads localStorage['jos-theme'] and sets the
       data-theme attribute before paint (prevents flash of wrong theme).
    2. A <script defer src="../theme-toggle.js"></script> tag that loads the
       shared script, which self-installs the toggle button on DOMContentLoaded.

Both tags are bracketed by the INJECTION_MARKER comment so the script is
idempotent (re-running is a no-op) and reversible via --remove.

The theme-toggle.js file itself is not copied by this script. It lives at the
site root next to jos.css (see jos-latex/styles/theme-toggle.js). Pages
reference it via ../theme-toggle.js, matching how ../jos.css is referenced.
"""

import argparse
import re
import sys
from pathlib import Path


INJECTION_MARKER = "<!-- THEME-TOGGLE -->"
INJECTION_END_MARKER = "<!-- /THEME-TOGGLE -->"


def injection_block(script_src: str) -> str:
    return (
        f"{INJECTION_MARKER}\n"
        "<script>try{var t=localStorage.getItem('jos-theme');"
        "if(t==='light'||t==='dark')"
        "document.documentElement.setAttribute('data-theme',t)}"
        "catch(e){}</script>\n"
        f'<script defer src="{script_src}"></script>\n'
        f"{INJECTION_END_MARKER}\n"
    )


HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
BLOCK_RE = re.compile(
    re.escape(INJECTION_MARKER) + r".*?" + re.escape(INJECTION_END_MARKER) + r"\n?",
    re.DOTALL,
)


def inject(path: Path, script_src: str, dry_run: bool) -> bool:
    content = path.read_text(encoding="utf-8", errors="replace")
    if INJECTION_MARKER in content:
        return False
    match = HEAD_CLOSE_RE.search(content)
    if not match:
        print(f"  Warning: no </head> in {path.name}", file=sys.stderr)
        return False
    block = injection_block(script_src)
    new_content = content[: match.start()] + block + content[match.start() :]
    if dry_run:
        print(f"  Would inject: {path.name}")
    else:
        path.write_text(new_content, encoding="utf-8")
    return True


def remove(path: Path, dry_run: bool) -> bool:
    content = path.read_text(encoding="utf-8", errors="replace")
    if INJECTION_MARKER not in content:
        return False
    new_content = BLOCK_RE.sub("", content)
    if dry_run:
        print(f"  Would remove from: {path.name}")
    else:
        path.write_text(new_content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, help="HTML directory to process")
    parser.add_argument(
        "--script-src",
        default="../theme-toggle.js",
        help="Value for the <script src=...> attribute (default: ../theme-toggle.js)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()

    dest = Path(args.dest)
    if not dest.is_dir():
        print(f"Error: {dest} is not a directory", file=sys.stderr)
        return 1

    verb = "Removing from" if args.remove else "Injecting into"
    print(f"{verb} {dest}{' (dry run)' if args.dry_run else ''}")

    modified = 0
    scanned = 0
    for path in sorted(dest.glob("*.html")):
        scanned += 1
        if args.remove:
            ok = remove(path, args.dry_run)
        else:
            ok = inject(path, args.script_src, args.dry_run)
        if ok:
            modified += 1

    print(f"  {scanned} files scanned, {modified} modified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
