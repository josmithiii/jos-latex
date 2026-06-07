#!/usr/bin/env python3
"""
validate-exercises.py - Structural validation of the course exercises JSON.

Checks the failure modes that actually bite (see ExercisesDeveloperGuide.md):
  - JSON parses
  - every `page` names an existing HTML file (else the exercise silently
    never renders)
  - `id`s are globally unique (ids are localStorage progress keys)
  - `correct` is one of the option ids
  - each exercise has 2..4 options with unique option ids
  - required fields are present

Does NOT check the placement rule (exercise must follow, not precede, the
material it tests) - that requires reading page prose; see the guide.

Usage:
    python3 validate-exercises.py [--exercises PATH] [--html-dir DIR]

Exit status is non-zero if any problem is found (fail fast).
"""

import argparse
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = ("id", "page", "type", "question", "options", "correct")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-dir", default="mdftHTML",
                    help="Directory containing HTML files (e.g. mdftHTML, saspHTML)")
    ap.add_argument("--exercises", default=None,
                    help="Exercises JSON (default: course/data/exercises/<book>-exercises.json)")
    args = ap.parse_args()

    html_dir = Path(args.html_dir)
    # Book-agnostic: derive the book name from the HTML dir (mdftHTML -> "mdft").
    book = html_dir.name[:-4] if html_dir.name.endswith("HTML") else html_dir.name
    ex_path = Path(args.exercises) if args.exercises \
        else Path(f"course/data/exercises/{book}-exercises.json")

    try:
        data = json.loads(ex_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"*** Exercises JSON failed to load: {e}", file=sys.stderr)
        return 1

    exercises = data.get("exercises")
    if not isinstance(exercises, list):
        print("*** Top-level 'exercises' array missing or not a list", file=sys.stderr)
        return 1

    if not html_dir.is_dir():
        print(f"*** HTML dir not found: {html_dir} (run 'make html' first?)", file=sys.stderr)
        return 1
    existing_pages = {p.name for p in html_dir.glob("*.html")}

    problems: list[str] = []
    seen_ids: dict[str, int] = {}

    for i, e in enumerate(exercises):
        where = e.get("id") or f"index {i}"

        missing = [f for f in REQUIRED_FIELDS if f not in e]
        if missing:
            problems.append(f"{where}: missing required field(s): {', '.join(missing)}")
            continue  # remaining checks assume fields exist

        eid = e["id"]
        if eid in seen_ids:
            problems.append(f"{eid}: duplicate id (also at index {seen_ids[eid]})")
        else:
            seen_ids[eid] = i

        if e["page"] not in existing_pages:
            problems.append(f"{eid}: page '{e['page']}' does not exist in {html_dir} "
                            f"(exercise would silently never render)")

        options = e["options"]
        if not isinstance(options, list) or not (2 <= len(options) <= 4):
            problems.append(f"{eid}: expected 2..4 options, got "
                            f"{len(options) if isinstance(options, list) else type(options).__name__}")
            continue
        opt_ids = [o.get("id") for o in options]
        if len(set(opt_ids)) != len(opt_ids):
            problems.append(f"{eid}: duplicate option ids {opt_ids}")
        if e["correct"] not in opt_ids:
            problems.append(f"{eid}: correct='{e['correct']}' is not among option ids {opt_ids}")

    if problems:
        print(f"*** {len(problems)} problem(s) in {ex_path} ({len(exercises)} exercises):",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"Exercises JSON: valid - {len(exercises)} exercises, "
          f"all pages exist, ids unique, answers consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
