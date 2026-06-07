#!/usr/bin/env python3
"""
Generate page-metadata.json + outline.json from a JOS book's HTML.

Book-agnostic: the book name is derived from the HTML directory
(e.g. mdftHTML -> "mdft"), which also sets the default .aux file and the
root page name. Shared across all books via /w/jos-latex/course/py/.

Parses the LaTeX2HTML output in <book>HTML/ to extract:
- Title and section number (from <book>.aux + labels.pl)
- Chapter/section hierarchy
- Navigation (prev/next/up)
- Estimated reading time
- Concepts (from anchor IDs)
- An ordered, numbered outline (from the front page's Child-Links TOC)

Usage:
    python generate-page-metadata.py [--html-dir <book>HTML] [--aux <book>.aux]
"""

import argparse
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class PageMetadata:
    title: str = ""
    sectionNumber: str = ""  # e.g. "3.5" or "A.1.2"; "" for front/back matter
    chapter: str = ""
    depth: int = 0  # 0=top, 1=chapter, 2=section, 3=subsection
    prev: Optional[str] = None
    next: Optional[str] = None
    up: Optional[str] = None
    hasProblems: bool = False
    estimatedReadingMinutes: int = 0
    concepts: list[str] = field(default_factory=list)
    wordCount: int = 0
    hasEquations: bool = False
    hasFigures: bool = False


class HTMLMetadataParser(HTMLParser):
    """Parse HTML file to extract metadata."""

    def __init__(self):
        super().__init__()
        self.metadata = PageMetadata()
        self.in_title = False
        self.in_h1 = False
        self.in_h2 = False
        self.in_body = False
        self.in_nav_panel = False
        self.title_text = ""
        self.h1_text = ""
        self.h2_text = ""
        self.body_text = ""
        self.current_tag = ""
        self.concepts: set[str] = set()
        self.equation_count = 0
        self.figure_count = 0
        self.link_rels: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        self.current_tag = tag.lower()
        attrs_dict = {k.lower(): v for k, v in attrs if v is not None}

        if tag.lower() == "title":
            self.in_title = True
            self.title_text = ""
        elif tag.lower() == "h1":
            self.in_h1 = True
            self.h1_text = ""
        elif tag.lower() == "h2":
            self.in_h2 = True
            self.h2_text = ""
        elif tag.lower() == "body":
            self.in_body = True
        elif tag.lower() == "link":
            rel = attrs_dict.get("rel", "").lower()
            href = attrs_dict.get("href", "")
            if rel in ("next", "previous", "up") and href:
                self.link_rels[rel] = href
        elif tag.lower() == "a":
            name = attrs_dict.get("name", "")
            if name:
                # Extract semantic concept IDs
                if name.startswith("sec:") or name.startswith("chap:"):
                    self.concepts.add(name)
                elif name.startswith("eq:"):
                    self.concepts.add(name)
        elif tag.lower() == "img":
            src = attrs_dict.get("src", "")
            if src:
                # Count equations (typically from latex2html)
                if "img" in src and src.endswith(".png"):
                    self.equation_count += 1
                # Count figures
                if "eps" in src or "fig" in src.lower():
                    self.figure_count += 1

        # Detect navigation panel to exclude from word count
        if tag.lower() == "strong":
            pass  # Navigation panels start with STRONG

    def handle_endtag(self, tag: str):
        if tag.lower() == "title":
            self.in_title = False
        elif tag.lower() == "h1":
            self.in_h1 = False
        elif tag.lower() == "h2":
            self.in_h2 = False
        elif tag.lower() == "body":
            self.in_body = False

    def handle_data(self, data: str):
        if self.in_title:
            self.title_text += data
        if self.in_h1:
            self.h1_text += data
        if self.in_h2:
            self.h2_text += data
        if self.in_body:
            self.body_text += data

    def get_metadata(self) -> PageMetadata:
        # Clean up title
        title = self.title_text.strip()
        title = re.sub(r'\s+', ' ', title)

        # Determine depth based on heading structure and title patterns
        depth = 2  # Default to section
        if "Contents" in title or title == "Mathematics of the Discrete Fourier Transform (DFT)":
            depth = 0
        elif self.h1_text.strip() and not self.h2_text.strip():
            depth = 1  # Chapter level
        elif "Problems" in title or "Exercises" in title:
            depth = 2

        # Extract chapter from up link or title
        chapter = ""
        if "previous" in self.link_rels:
            # Try to infer chapter from navigation
            pass

        # Calculate word count (rough estimate, excluding navigation)
        # Remove navigation panel text patterns
        body_clean = self.body_text
        body_clean = re.sub(r'Next\s*\|\s*Prev\s*\|\s*Up\s*\|\s*Top\s*\|\s*Index', '', body_clean)
        body_clean = re.sub(r'\s+', ' ', body_clean)
        words = len(body_clean.split())

        # Estimate reading time: ~200 words/min for technical text
        # Add time for equations and figures
        equation_time = self.equation_count * 0.5  # 30 seconds per equation
        figure_time = self.figure_count * 0.25  # 15 seconds per figure
        reading_minutes = max(1, int((words / 200) + equation_time + figure_time))

        return PageMetadata(
            title=title,
            chapter=chapter,
            depth=depth,
            prev=self.link_rels.get("previous"),
            next=self.link_rels.get("next"),
            up=self.link_rels.get("up"),
            hasProblems="Problems" in title or "Exercises" in title,
            estimatedReadingMinutes=reading_minutes,
            concepts=sorted(list(self.concepts)),
            wordCount=words,
            hasEquations=self.equation_count > 0,
            hasFigures=self.figure_count > 0,
        )


def determine_chapter_hierarchy(
    metadata_dict: dict[str, PageMetadata], top_pages: set[str]
) -> dict[str, PageMetadata]:
    """Walk the navigation tree to determine chapter names and depths."""

    # First pass: identify chapter-level pages (those whose "up" is a top page)
    chapter_pages: set[str] = set()

    for filename, meta in metadata_dict.items():
        if meta.up in top_pages:
            chapter_pages.add(filename)
            meta.depth = 1  # Chapter level

        # Also check for chapter concepts
        if any(c.startswith("chap:") for c in meta.concepts):
            chapter_pages.add(filename)
            meta.depth = 1

    # Second pass: walk from each page up to find its chapter
    for filename, meta in metadata_dict.items():
        if filename in chapter_pages:
            # Chapter pages have themselves as their chapter
            meta.chapter = meta.title
            continue

        current = filename
        visited: set[str] = set()
        while current and current not in visited:
            visited.add(current)
            current_meta = metadata_dict.get(current)
            if not current_meta:
                break
            if current in chapter_pages:
                meta.chapter = current_meta.title
                break
            current = current_meta.up

    # Third pass: determine depth based on distance from chapter
    for filename, meta in metadata_dict.items():
        if filename in top_pages:
            meta.depth = 0
            continue
        if filename in chapter_pages:
            meta.depth = 1
            continue

        # Count hops to chapter
        current = meta.up
        depth = 2  # Minimum depth for non-chapter pages
        visited: set[str] = set()
        while current and current not in visited and current not in chapter_pages:
            visited.add(current)
            current_meta = metadata_dict.get(current)
            if not current_meta:
                break
            depth += 1
            current = current_meta.up
        meta.depth = depth

    return metadata_dict


def parse_aux_numbers(aux_path: Path) -> dict[str, str]:
    """Map sectioning label -> section number (e.g. 'sec:foo' -> '3.5').

    Reads LaTeX .aux entries of the form
        \\newlabel{sec:foo}{{3.5}{7}{Title}{section.123}{}}
    keeping only sectioning labels (sec:/chap:/app:), first occurrence wins
    (= document order).
    """
    numbers: dict[str, str] = {}
    if not aux_path.exists():
        print(f"Warning: aux file '{aux_path}' not found; section numbers unavailable")
        return numbers
    text = aux_path.read_text(encoding="utf-8", errors="replace")
    pat = re.compile(r"\\newlabel\{((?:sec|chap|app):[^}]*)\}\{\{([^}]*)\}")
    for m in pat.finditer(text):
        key, num = m.group(1), m.group(2).strip()
        if num and key not in numbers:
            numbers[key] = num
    return numbers


def parse_labels_pl(labels_path: Path) -> dict[str, str]:
    """Map label -> HTML filename, from latex2html's labels.pl."""
    mapping: dict[str, str] = {}
    if not labels_path.exists():
        print(f"Warning: '{labels_path}' not found; cannot map labels to pages")
        return mapping
    text = labels_path.read_text(encoding="utf-8", errors="replace")
    pat = re.compile(
        r"\$key = q/([^/]+)/;\s*\n\$external_labels\{\$key\}\s*=\s*"
        r'"\$URL/"\s*\.\s*q\|([^|]+)\|'
    )
    for m in pat.finditer(text):
        mapping[m.group(1)] = m.group(2)
    return mapping


def build_section_numbers(aux_path: Path, labels_path: Path) -> dict[str, str]:
    """Map HTML filename -> its owning section number.

    A page may host a section plus its subsections; the owner is the
    shallowest number (fewest dots, then shortest), e.g. '3.5' over '3.5.1'.
    """
    nums = parse_aux_numbers(aux_path)
    files = parse_labels_pl(labels_path)
    by_file: dict[str, list[str]] = {}
    for label, num in nums.items():
        f = files.get(label)
        if f:
            by_file.setdefault(f, []).append(num)
    return {
        f: min(cands, key=lambda n: (n.count("."), len(n)))
        for f, cands in by_file.items()
    }


def parse_toc_outline(index_path: Path, sec_numbers: dict[str, str]) -> list[dict]:
    """Build an ordered, nested outline from the front page's Child-Links TOC.

    Returns a flat list (in reading order) of
        {file, title, num, depth}
    where depth starts at 1 for top-level entries.
    """
    if not index_path.exists():
        print(f"Warning: '{index_path}' not found; outline will be empty")
        return []
    text = index_path.read_text(encoding="latin-1", errors="replace")
    start = text.find("<!--Table of Child-Links-->")
    end = text.find("<!--End of Table of Child-Links-->")
    region = text[start:end] if start != -1 and end != -1 else text

    token = re.compile(
        r"(<UL\b)|(</UL>)|<A\s+[^>]*HREF=\"([^\"#]+)\"[^>]*>(.*?)</A>",
        re.I | re.S,
    )
    outline: list[dict] = []
    depth = 0
    for m in token.finditer(region):
        if m.group(1):
            depth += 1
        elif m.group(2):
            depth = max(0, depth - 1)
        else:
            href, inner = m.group(3), m.group(4)
            if not href.endswith(".html"):
                continue
            title = re.sub(r"<[^>]+>", "", inner)
            title = re.sub(r"\s+", " ", title).strip()
            outline.append(
                {
                    "file": href,
                    "title": title,
                    "num": sec_numbers.get(href, ""),
                    "depth": depth,
                }
            )

    # Pass 1 (ancestor from descendant): fill missing numbers on container
    # rows, e.g. chapter "1" with no chap: label but children "1.1", "1.2".
    # A numbered entry has exactly `depth` dotted components, so an unnumbered
    # entry at depth D inherits the first D components of its first numbered
    # descendant. True front/back matter has no numbered descendants and stays
    # blank.
    for i, e in enumerate(outline):
        if e["num"]:
            continue
        for j in range(i + 1, len(outline)):
            if outline[j]["depth"] <= e["depth"]:
                break
            child_num = outline[j]["num"]
            if child_num:
                parts = child_num.split(".")
                if len(parts) >= e["depth"]:
                    e["num"] = ".".join(parts[: e["depth"]])
                break

    # Pass 2 (parent number for unnumbered leaves): unnumbered pages deeper
    # than the book's numbering depth (e.g. \paragraph nodes like "Relation to
    # Stretch Theorem") inherit their nearest numbered ancestor's number, for
    # location context. Front/back matter has no numbered ancestor and stays
    # blank.
    last_num_by_depth: dict[int, str] = {}
    for e in outline:
        d = e["depth"]
        for k in [k for k in last_num_by_depth if k >= d]:
            del last_num_by_depth[k]
        if e["num"]:
            last_num_by_depth[d] = e["num"]
        else:
            ancestors = [last_num_by_depth[k] for k in sorted(last_num_by_depth) if k < d]
            if ancestors:
                e["num"] = ancestors[-1]
                last_num_by_depth[d] = e["num"]
    return outline


def parse_html_file(filepath: Path) -> PageMetadata:
    """Parse a single HTML file and extract metadata."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return PageMetadata(title=filepath.stem)

    parser = HTMLMetadataParser()
    try:
        parser.feed(content)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return PageMetadata(title=filepath.stem)

    return parser.get_metadata()


def generate_metadata(
    html_dir: Path, page_numbers: dict[str, str], top_pages: set[str]
) -> dict[str, dict]:
    """Generate metadata for all HTML files in directory.

    page_numbers maps HTML filename -> section number (including numbers
    inherited by unnumbered \\paragraph pages from their parent).
    top_pages are the book's root HTML files (e.g. {"mdft.html", "index.html"}).
    """
    metadata: dict[str, PageMetadata] = {}

    html_files = sorted(html_dir.glob("*.html"))
    print(f"Found {len(html_files)} HTML files in {html_dir}")

    for filepath in html_files:
        filename = filepath.name
        # Skip non-content files
        if filename.startswith("ORIG_") or filename.startswith("labels."):
            continue

        meta = parse_html_file(filepath)
        metadata[filename] = meta

    # Determine chapter hierarchy and depths
    metadata = determine_chapter_hierarchy(metadata, top_pages)

    # Attach section numbers (e.g. "3.5", or a parent number for \paragraph pages)
    for filename, meta in metadata.items():
        if filename in page_numbers:
            meta.sectionNumber = page_numbers[filename]
    print(f"Mapped section numbers for {len(page_numbers)} pages")

    # Convert to serializable dict
    result = {}
    for filename, meta in metadata.items():
        d = asdict(meta)
        # Remove None values for cleaner JSON
        result[filename] = {k: v for k, v in d.items() if v is not None and v != "" and v != []}

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate page-metadata.json + outline.json from a JOS book's HTML"
    )
    parser.add_argument("--html-dir", default="mdftHTML",
                        help="Directory containing HTML files (e.g. mdftHTML, saspHTML)")
    parser.add_argument("--output", default="course/data/page-metadata.json", help="Output JSON file")
    parser.add_argument("--aux", default=None,
                        help="LaTeX .aux file for section numbers (default: <book>.aux)")
    parser.add_argument("--outline-output", default="course/data/outline.json", help="Outline JSON file")
    args = parser.parse_args()

    html_dir = Path(args.html_dir)
    if not html_dir.exists():
        print(f"Error: HTML directory '{html_dir}' not found")
        return 1

    # Derive the book name from the HTML dir (mdftHTML -> "mdft"); this sets the
    # default .aux file and the set of root page names.
    book = html_dir.name[:-4] if html_dir.name.endswith("HTML") else html_dir.name
    aux_path = Path(args.aux) if args.aux else Path(f"{book}.aux")
    top_pages = {f"{book}.html", "index.html"}
    print(f"Book: {book!r} (aux: {aux_path}, top pages: {sorted(top_pages)})")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the ordered, nested outline first; its parent-inheritance pass is
    # the source of truth for every page's section number (including unnumbered
    # \paragraph pages), so derive the page->number map from it.
    sec_numbers = build_section_numbers(aux_path, html_dir / "labels.pl")
    outline = parse_toc_outline(html_dir / "index.html", sec_numbers)
    page_numbers = dict(sec_numbers)
    for e in outline:
        if e["num"]:
            page_numbers[e["file"]] = e["num"]

    print(f"Parsing HTML files from: {html_dir}")
    metadata = generate_metadata(html_dir, page_numbers, top_pages)

    print(f"Writing metadata for {len(metadata)} pages to: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Write the outline (TOC) for the course panel
    outline_path = Path(args.outline_output)
    outline_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing outline ({len(outline)} entries) to: {outline_path}")
    with open(outline_path, 'w', encoding='utf-8') as f:
        json.dump(outline, f, indent=2, ensure_ascii=False)

    # Print summary statistics
    total_reading_time = sum(m.get("estimatedReadingMinutes", 0) for m in metadata.values())
    pages_with_problems = sum(1 for m in metadata.values() if m.get("hasProblems"))
    pages_with_equations = sum(1 for m in metadata.values() if m.get("hasEquations"))

    print(f"\nSummary:")
    print(f"  Total pages: {len(metadata)}")
    print(f"  Total estimated reading time: {total_reading_time} minutes ({total_reading_time // 60} hours)")
    print(f"  Pages with problems: {pages_with_problems}")
    print(f"  Pages with equations: {pages_with_equations}")

    return 0


if __name__ == "__main__":
    exit(main())
