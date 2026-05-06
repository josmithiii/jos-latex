#!/usr/bin/env python3
"""
inject-course.py - Inject course enhancement loader into HTML files

Usage:
    python inject-course.py              # Inject into all HTML files in {NAME}HTML/
    python inject-course.py --dry-run    # Show what would be done
    python inject-course.py --remove     # Remove injected script tags
    python inject-course.py --dest DIR   # Inject into DIR instead of {NAME}HTML/

This script is idempotent - running it multiple times will not duplicate injections.
"""

import os
import re
import sys
from pathlib import Path

# Marker comment to identify our injection
INJECTION_MARKER = '<!-- COURSE-INJECT -->'

def make_injection_script(name: str) -> str:
    """Build the injection block. Sets window.JOS_COURSE_NAME so the loader
    knows which book this is (used for per-book exercises file and
    localStorage keys). On CCRMA, the name can be derived from the URL path
    (e.g. /~jos/mdft/...), but localhost serves from the HTML dir directly,
    so we set it explicitly here."""
    import json as _json
    return (
        f'{INJECTION_MARKER}\n'
        f'<script>window.JOS_COURSE_NAME = {_json.dumps(name)};</script>\n'
        f'<script src="course-inject.js"></script>\n'
    )

# Match any prior injection block (legacy single-script or new two-script
# form) so re-injecting upgrades existing files in place.
INJECTION_BLOCK_RE = re.compile(
    re.escape(INJECTION_MARKER) +
    r'\n(?:[ \t]*<script(?:\s[^>]*)?>[^<]*</script>\n)+',
)

# Meta tag to discourage Safari Reader mode (must be in <head> before page loads)
HEAD_MARKER = '<!-- COURSE-HEAD -->'
HEAD_INJECTION = f'''{HEAD_MARKER}
<meta name="apple-mobile-web-app-capable" content="yes">
'''

def find_html_dir(dest: str | None = None) -> Path:
    """Find the target HTML directory."""
    script_dir = Path(__file__).parent

    if dest:
        html_dir = Path(dest)
    else:
        # Auto-detect: look for {name}HTML directories
        html_dirs = list(script_dir.glob('*HTML'))
        html_dirs = [d for d in html_dirs if d.is_dir() and not d.name.startswith('.')]
        if len(html_dirs) == 1:
            html_dir = html_dirs[0]
        elif len(html_dirs) > 1:
            print(f"Error: Multiple HTML directories found: {[d.name for d in html_dirs]}", file=sys.stderr)
            print("Please specify with --dest", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"Error: No *HTML directory found in {script_dir}", file=sys.stderr)
            sys.exit(1)

    if not html_dir.exists():
        print(f"Error: {html_dir} not found", file=sys.stderr)
        sys.exit(1)
    return html_dir


def inject_into_file(filepath: Path, name: str, dry_run: bool = False) -> bool:
    """Inject the course loader into a single HTML file.

    Returns True if file was modified, False if already up to date or skipped.
    Idempotent: if the file already has the exact target injection block, it
    is left alone. If it has a legacy/older block, that block is replaced.
    """
    content = filepath.read_text(encoding='utf-8', errors='replace')
    target_block = make_injection_script(name)

    # Already up to date — leave the body as-is.
    if target_block in content:
        new_content = content
    else:
        # Strip any prior injection block, then insert the current one.
        cleaned = INJECTION_BLOCK_RE.sub('', content)

        body_close_pattern = re.compile(r'(</body>)', re.IGNORECASE)
        match = body_close_pattern.search(cleaned)
        if not match:
            print(f"  Warning: No </body> found in {filepath.name}", file=sys.stderr)
            return False

        insert_pos = match.start()
        new_content = cleaned[:insert_pos] + target_block + cleaned[insert_pos:]

    # Also inject into <head> to discourage Safari Reader mode
    if HEAD_MARKER not in new_content:
        head_close_pattern = re.compile(r'(</head>)', re.IGNORECASE)
        head_match = head_close_pattern.search(new_content)
        if head_match:
            head_pos = head_match.start()
            new_content = new_content[:head_pos] + HEAD_INJECTION + new_content[head_pos:]

    if new_content == content:
        return False

    if dry_run:
        print(f"  Would inject into: {filepath.name}")
    else:
        filepath.write_text(new_content, encoding='utf-8')

    return True


def remove_from_file(filepath: Path, dry_run: bool = False) -> bool:
    """Remove the injected course loader from a single HTML file.

    Returns True if file was modified, False if injection not found.
    Handles legacy and current injection forms via regex.
    """
    content = filepath.read_text(encoding='utf-8', errors='replace')

    new_content, n = INJECTION_BLOCK_RE.subn('', content)
    new_content = new_content.replace(HEAD_INJECTION, '')

    if new_content == content:
        return False

    if dry_run:
        print(f"  Would remove from: {filepath.name}")
    else:
        filepath.write_text(new_content, encoding='utf-8')

    return True


def copy_course_assets(html_dir: Path, dry_run: bool = False) -> None:
    """Copy course assets into the HTML directory."""
    script_dir = Path(__file__).parent
    source_inject = script_dir / 'course-inject.js'
    source_course = script_dir / 'course'
    dest_inject = html_dir / 'course-inject.js'
    dest_course = html_dir / 'course'

    if dry_run:
        print(f"  Would copy course-inject.js to {html_dir}")
        print(f"  Would copy course/ directory to {html_dir}")
        return

    # Copy course-inject.js
    if source_inject.exists():
        import shutil
        shutil.copy2(source_inject, dest_inject)
        print(f"  Copied course-inject.js")

    # Copy course/ directory
    if source_course.exists():
        import shutil
        if dest_course.exists():
            shutil.rmtree(dest_course)
        shutil.copytree(source_course, dest_course)
        print(f"  Copied course/ directory")


_KEYWORDS_RE = re.compile(
    r'<META\s+NAME\s*=\s*"keywords"\s+CONTENT\s*=\s*"([^"]+)"',
    re.IGNORECASE,
)


def derive_book_name(html_dir: Path, override: str | None = None) -> str:
    """Derive the lowercase book name (e.g. 'mdft', 'sasp') used for per-book
    exercise filenames and localStorage keys. Strategy:
      1. Explicit --name override.
      2. <META NAME="keywords" CONTENT="..."> in About_this_document.html
         (authoritative — emitted by latex2html for every book in this series).
      3. Strip trailing 'HTML' from the html_dir name (e.g. 'mdftHTML' -> 'mdft').
      4. Fall back to the parent directory name.
    """
    if override:
        return override.lower()

    about = html_dir / 'About_this_document.html'
    if about.is_file():
        try:
            text = about.read_text(encoding='utf-8', errors='replace')
            m = _KEYWORDS_RE.search(text)
            if m:
                return m.group(1).strip().lower()
        except OSError:
            pass

    stem = html_dir.name
    if stem.endswith('HTML') and len(stem) > 4:
        return stem[:-4].lower()
    return html_dir.parent.name.lower()


def main():
    dry_run = '--dry-run' in sys.argv
    remove = '--remove' in sys.argv

    # Parse --dest and --name arguments
    dest = None
    name_override = None
    for i, arg in enumerate(sys.argv):
        if arg == '--dest' and i + 1 < len(sys.argv):
            dest = sys.argv[i + 1]
        elif arg == '--name' and i + 1 < len(sys.argv):
            name_override = sys.argv[i + 1]

    html_dir = find_html_dir(dest)
    name = derive_book_name(html_dir, name_override)
    # Filter to only actual files (not broken symlinks)
    html_files = sorted(f for f in html_dir.glob('*.html') if f.is_file())

    print(f"Found {len(html_files)} HTML files in {html_dir}")
    if not remove:
        print(f"Book name: {name!r} (window.JOS_COURSE_NAME)")

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    modified = 0
    skipped = 0

    if remove:
        print("Removing course injections...")
        for filepath in html_files:
            if remove_from_file(filepath, dry_run):
                modified += 1
            else:
                skipped += 1
    else:
        print("Injecting course loader...")
        for filepath in html_files:
            if inject_into_file(filepath, name, dry_run):
                modified += 1
            else:
                skipped += 1

        # Copy assets
        print("\nCopying course assets...")
        copy_course_assets(html_dir, dry_run)

    print(f"\nDone: {modified} files {'would be ' if dry_run else ''}modified, {skipped} skipped")


if __name__ == '__main__':
    main()
