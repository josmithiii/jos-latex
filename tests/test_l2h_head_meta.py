"""Tests that l2h-mathjax-init.pl puts the dark-mode opt-out metadata in every page's <HEAD>.

Runs the real latex2html on a tiny document whose init file requires
l2h-mathjax-init.pl, as the books' dot-latex2html-init files do.  A missing
latex2html is a hard failure, not a skip.

Run:  cd /w/jos-latex && python3 -m pytest tests/test_l2h_head_meta.py
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

JOS_LATEX = Path(__file__).resolve().parent.parent

DOC = r"""\documentclass{article}
\begin{document}
\section{One}
Hello.
\section{Two}
World.
\end{document}
"""


def test_every_page_head_has_dark_mode_opt_out(tmp_path: Path) -> None:
    l2h = shutil.which("latex2html")
    assert l2h, "latex2html not found on PATH"
    (tmp_path / "doc.tex").write_text(DOC)
    (tmp_path / "doc.l2h").write_text(f'require "{JOS_LATEX}/l2h-mathjax-init.pl";\n1;\n')
    (tmp_path / "out").mkdir()  # latex2html -dir requires an existing directory
    result = subprocess.run(
        [l2h, "-dir", "out", "-init_file", "doc.l2h", "-split", "2", "doc.tex"],
        cwd=tmp_path, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    pages = sorted((tmp_path / "out").glob("*.html"))
    assert len(pages) >= 2, "expected several split pages"
    for page in pages:
        head = page.read_text(errors="replace").split("</HEAD>", 1)[0]
        assert '<META NAME="darkreader-lock">' in head, page.name
        assert '<META NAME="color-scheme" CONTENT="light dark">' in head, page.name
        assert 'NAME="Generator" CONTENT="LaTeX2HTML v' in head, page.name  # default kept
