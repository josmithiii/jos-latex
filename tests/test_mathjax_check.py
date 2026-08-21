"""Tests for tools/mathjax-check.js.

Runs the real checker (node + mathjax-full + parse5, installed in
tools/node_modules via `npm ci`) on small synthetic HTML trees.  A missing
node or node_modules is a hard failure, not a skip.

Run:  cd /w/jos-latex && python3 -m pytest tests/test_mathjax_check.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

JOS_LATEX = Path(__file__).resolve().parent.parent
CHECKER = JOS_LATEX / "tools" / "mathjax-check.js"
NODE_MODULES = JOS_LATEX / "tools" / "node_modules"

CONFIG_JS = r"""
window.MathJax = {
  loader: {load: ['[tex]/ams', '[tex]/textmacros', '[tex]/boldsymbol', '[tex]/unicode']},
  tex: {
    packages: {'[+]': ['ams', 'textmacros', 'boldsymbol', 'unicode']},
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    processEscapes: false,
    processEnvironments: true,
    tags: 'ams',
    macros: {
      foo: 'x',
      zbox: ['\\boxed{#1}', 1],
      textcircled: ['\\unicode{x24C7}', 1]
    }
  },
  options: {
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
  }
};
"""

# latex2html-style page: uppercase tags, a stray </BLOCKQUOTE>, and math in
# the three forms l2h emits (inline span, display div, top-level environment).
CLEAN_PAGE = r"""<!DOCTYPE html>
<HTML>
<HEAD>
<TITLE>Clean</TITLE>
<script src="mathjax-config.js"></script>
</HEAD>
<BODY>
<P>Inline <SPAN CLASS="MATH">\(\foo + \frac{1}{2}\)</SPAN> and
<SPAN CLASS="MATH">\(\boldsymbol{x}^{\hbox{\scriptsize\textcircled{\tiny R}}}\)</SPAN>.</P>
<BLOCKQUOTE>quoted</BLOCKQUOTE></BLOCKQUOTE>
<DIV CLASS="MATHDISPLAY">\[\zbox{a &lt; b}\]</DIV>
<DIV CLASS="MATHDISPLAY">\begin{equation}c = d\end{equation}</DIV>
<PRE>\(not math: inside PRE\)</PRE>
</BODY>
</HTML>
"""

BAD_PAGE = r"""<HTML><HEAD><TITLE>Bad</TITLE></HEAD><BODY>
<P>line 2</P>
<DIV CLASS="MATHDISPLAY">\[\xvnu_0 = \alpha_0 \underline{s}_0\]</DIV>
<P><SPAN CLASS="MATH">\(\cancel{x}\)</SPAN></P>
<P><SPAN CLASS="MATH">\(\fbox{ \begin{tabular}{c} t \end{tabular} }\)</SPAN></P>
<P><SPAN CLASS="MATH">\(\begin{tabular}{c} t \end{tabular}\)</SPAN></P>
<P><SPAN CLASS="MATH">\(\frac{1}\)</SPAN></P>
</BODY></HTML>
"""


def run_checker(tree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert CHECKER.is_file(), f"missing {CHECKER}"
    assert NODE_MODULES.is_dir(), f"run `npm ci` in {NODE_MODULES.parent}"
    return subprocess.run(
        ["node", str(CHECKER), *args, str(tree)],
        capture_output=True, text=True, check=False,
    )


def make_tree(root: Path, pages: dict[str, str], config: str | None = CONFIG_JS) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    if config is not None:
        (root / "mathjax-config.js").write_text(config)
    for name, body in pages.items():
        (root / name).write_text(body)
    return root


def test_clean_tree_passes(tmp_path: Path) -> None:
    tree = make_tree(tmp_path / "html", {"clean.html": CLEAN_PAGE})
    r = run_checker(tree)
    assert r.returncode == 0, r.stdout + r.stderr
    # 4 expressions: two inline, one \[..\], one top-level equation; the
    # one inside <PRE> is skipped like the browser does.
    assert "mathjax-check: OK -- 1 file(s), 4 expressions" in r.stdout
    assert "unicode" in r.stdout  # package list echoed from the config


def test_reports_undefined_autoload_env_and_parse_errors(tmp_path: Path) -> None:
    tree = make_tree(tmp_path / "html", {"bad.html": BAD_PAGE, "clean.html": CLEAN_PAGE})
    r = run_checker(tree)
    assert r.returncode == 1, r.stdout + r.stderr
    out = r.stdout
    bad = str(tree / "bad.html")
    # Undefined document macro that leaked through latex2html, with line number.
    assert f"{bad}:3: [UNDEFINED] Undefined control sequence \\xvnu" in out
    # Command the browser would fetch via autoload: flagged with the package.
    assert "[AUTOLOAD] Undefined control sequence \\cancel" in out
    assert "\\cancel needs [tex]/cancel in @MATHJAX_PACKAGES" in out
    # Text-mode environment inside math: inside \fbox (text mode) MathJax
    # complains about \begin itself; directly in math it is unknown.
    assert "[PARSE] \\begin is only supported in math mode" in out
    assert "[UNKNOWN-ENV] Unknown environment 'tabular'" in out
    # Generic parse error.
    assert "[PARSE] Missing argument for \\frac" in out
    # Summary table and final verdict.
    assert "problems by kind / command" in out
    assert "UNDEFINED  \\xvnu" in out
    assert "mathjax-check: FAIL -- 5 MathJax error(s) in 1/2 file(s)" in r.stderr


def test_summary_only(tmp_path: Path) -> None:
    tree = make_tree(tmp_path / "html", {"bad.html": BAD_PAGE})
    r = run_checker(tree, "--summary")
    assert r.returncode == 1
    assert "[UNDEFINED]" not in r.stdout  # per-error lines suppressed
    assert "UNDEFINED  \\xvnu" in r.stdout  # summary table kept


def test_inline_config_is_used(tmp_path: Path) -> None:
    # $MATHJAX_EXTERNAL_CONFIG = 0: config inlined in the page, no config file.
    page = CLEAN_PAGE.replace(
        '<script src="mathjax-config.js"></script>',
        "<script>" + CONFIG_JS + "</script>",
    )
    tree = make_tree(tmp_path / "html", {"clean.html": page}, config=None)
    r = run_checker(tree)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "4 expressions" in r.stdout


def test_missing_config_is_a_setup_error(tmp_path: Path) -> None:
    tree = make_tree(tmp_path / "html", {"clean.html": CLEAN_PAGE}, config=None)
    r = run_checker(tree)
    assert r.returncode == 2
    assert "no mathjax-config.js" in r.stderr


def test_unknown_package_in_config_is_a_setup_error(tmp_path: Path) -> None:
    cfg = CONFIG_JS.replace("'unicode']", "'unicode', 'nosuchpkg']")
    tree = make_tree(tmp_path / "html", {"clean.html": CLEAN_PAGE}, config=cfg)
    r = run_checker(tree)
    assert r.returncode == 2
    assert 'TeX package "nosuchpkg"' in r.stderr


@pytest.mark.parametrize("bad_dir", ["nonexistent", "empty"])
def test_bad_directory_arguments(tmp_path: Path, bad_dir: str) -> None:
    target = tmp_path / bad_dir
    if bad_dir == "empty":
        target.mkdir()
    r = run_checker(target)
    assert r.returncode == 2
