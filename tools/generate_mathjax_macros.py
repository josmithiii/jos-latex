#!/usr/bin/env python3
"""Generate MathJax macro definitions from jos-latex style files.

Parses LaTeX style files, extracts math-mode macro definitions,
translates LaTeX-isms to MathJax-compatible forms, and generates
a Perl file for use with latex2html's MathJax support.

Usage:
    python3 /w/jos-latex/tools/generate_mathjax_macros.py
"""

import re
import sys
from pathlib import Path

# Locate jos-latex root relative to this script (tools/ is one level down)
JOS_LATEX = Path(__file__).resolve().parent.parent
STYLES = JOS_LATEX / "styles"
OUTPUT = JOS_LATEX / "mathjax-macros.pl"

# Source files in dependency order
SOURCE_FILES = [
    STYLES / "stdmath.tex",
    STYLES / "cktdefs.tex",
    STYLES / "operators.tex",
    STYLES / "stddefs.tex",
    STYLES / "stdcommon.tex",
    STYLES / "wgtmac.tex",
]

# Macros to EXCLUDE (text-mode, structural, reference, index, etc.)
EXCLUDE_SET = {
    # === Environment shortcuts ===
    "BEQ", "EEQ", "BEQN", "EEQN", "BEQL", "EEQL",
    "BEQA", "EEQA", "bea", "eea", "beq", "eeq", "beqn", "eeqn",
    "beqa", "eeqa", "BEAS", "EEAS", "beas", "eeas",
    "BEASMI", "EEASMI", "BA", "EA",
    "BEAL", "EEAL", "beqnopt", "eeqnopt",
    "BIT", "EIT", "bit", "eit", "BNUM", "ENUM", "bnum", "enum",
    "BITC", "EITC", "BNUMC", "ENUMC",
    "beasda", "eeasda", "beqnl", "eeqnl",

    # === Reference macros ===
    "eq", "Eq", "eref", "erefb", "erefn", "Eref", "erefs", "Erefs",
    "eqn", "Eqn", "eqns", "epageref", "erefp", "epref", "eprefp",
    "elabel", "ilabel", "iref", "plabel", "pref", "ppageref",
    "ppref", "prefp", "sppref", "Sppref",
    "fref", "fbref", "fpageref", "frefp", "fpref", "fprefp",
    "Fref", "Fbref", "Fbpref", "Fpref", "frefs", "Frefs",
    "frefss", "Frefss", "frefr", "Frefr",
    "clabel", "cref", "crefs", "Cref", "Crefs", "crefr",
    "cpageref", "cpref", "cprefs", "Cpref", "Cprefs",
    "sref", "spageref", "srefp", "spref", "sprefp",
    "Sref", "Spref", "ssref", "srefs", "Srefs",
    "chrf", "chref", "chrefs", "Chref", "chlabel", "chpageref", "chpref",
    "aref", "Aref", "arefs", "alabel", "apageref", "apref",
    "Tref", "tref", "tpageref", "tpref",
    "lref", "Lref", "dref", "Dref",
    "thmref", "propref", "Thmref",
    "seclabel", "slabel", "kslabel",

    # === Section/structure macros ===
    "oursection", "oursectionncp", "oursubsection", "oursubsectionsamepage",
    "oursubsubsection", "mysection", "mysubsection", "mysubsubsection",
    "ksection", "ksectionalt", "ksubsection", "ksubsectionstar",
    "ksubsectionalt", "ksubsubsection", "ksubsubsectionalt",
    "ksubsubsectionstar",
    "kchapter", "kchapteralt", "kchlabel",
    "kappendix", "kappendixalt",
    "exsection", "labsection", "exsubsection", "labsubsection",
    "topic",

    # === Index macros ===
    "kdef", "kdefl", "kdefprepend", "kdefappend", "kdefne",
    "addindex", "kdefneq", "kdefq", "kdefgeneral", "xkdef",
    "kindex", "kwish", "kwishq", "kref", "krefe", "krefi",
    "krefiq", "krefq", "krefei", "ksetcontext", "knolink",
    "kemph",

    # === Graphics/figure macros ===
    "rawFigure", "figureskip",
    "figureCenterCapSize", "figureCenterCap", "figureLongCap",
    "maxheight", "wassevenin", "wassixpfivein", "wassixin",
    "wasfpfin", "wasfivein", "wasfourpfivein", "wasfourin",
    "wasthreepfivein", "wasthreein",
    "figwidth", "wgtFigScl",

    # === Font/layout macros ===
    "setlecfont", "xlabelsize", "mylabelsize", "leclabelsize",
    "psfragsize", "pointsize", "smallerpointsize", "largerpointsize",

    # === HTML/URL macros ===
    "ccrmahomepage", "josemail", "josEmailFootnoteWWWK", "josEmailFootnote",
    "hlink", "htmladdnormallinkfootNewAPI", "htmladdnormallinkfoottwo",
    "footurl", "googlesearch",
    "soundpathroot", "wavpath", "aiffpath", "mptpath", "soundpath",
    "soundexample", "soundexampleaiffmpt", "soundexamplewavmpt",
    "soundexamplewav", "soundexampleaiff", "soundexamplempt",
    "STK", "STKs", "STKfn", "stkclass", "stkclassfoot",
    "allpassfilterfoot", "mdftfoot", "mdftfootconv", "stkintrofoot",
    "planetccrma", "planetccrmafoot", "planetccrmalink",
    "faustlabstr", "faustintrofoot",
    "positionURL", "positionURLSL",
    "bookurl", "urlwofont", "urltilde", "urltj",
    "mytexttilde", "quotedtilde",

    # === Text-mode formatting ===
    "defn", "defnn", "Definition", "thm", "thml", "Theorem", "Property",
    "corr", "Corollary", "Lemma", "Prop",
    "Example", "Examples", "TheoremNo", "PropertyNo", "LemmaNo", "CorollaryNo",
    "pf", "Proof", "EndProof",
    "ie", "Ie", "Eg", "eg", "cf", "Cf", "viz",
    "Comment", "rmk", "fixme", "FIXME",
    "credit", "titlecredit",
    "solution", "solutionsee",
    "work", "thing",
    "tutEm", "tutOnly",
    "scream", "XXX",

    # === Box/layout macros ===
    "doublebox", "singlebox", "mybox", "quotebox", "quoteboxpn",
    "quoteboxfracw", "quotedzbox", "quotenobox", "quotedbox",
    "labeledeq", "labeledeqhold", "labeledeqnoeffectoncentering",
    "labeledeqnot", "eqlabel",

    # === List/toggle macros ===
    "localonly", "bookonly", "leconly", "booknot",
    "lcite", "lcitepp", "lecbook",
    "parinset", "parcenterline",

    # === Text-mode abbreviations ===
    "wi", "wis", "blt", "blts", "ai", "ais", "pr", "wg", "Wg",
    "dc", "whichbook", "beforebooks", "statespaceref",
    "biquad", "biquadsp",

    # === Problem point macros ===
    "twop", "twope", "threep", "fourp", "fivep", "fpe",
    "tenp", "ftp", "fifteenp", "sevenp", "twp", "twentyp",
    "twentyfivep", "twfp", "thirtyp", "fiftyp",

    # === Misc text/structural ===
    "makenavtoc", "docyear", "incldate",
    "Faust", "Faustsp", "faust", "faustsp",
    "Clang", "Cpp", "Cppsp", "cpp", "cpps", "gdb", "pd",
    "TM", "RM", "circleR",
    "tx", "briefrefs",
    "vcenteredhbox",
    "bmquote", "emquote", "noitemskip",
    "Tang", "Tinv", "Tanal",  # theorem numbers

    # === Sound/reverb text ===
    "zt", "zts",  # "z transform" (text mode)

    # === Newenvironment / newtheorem (not \newcommand) ===
    "eqnarrayda", "problem", "contentsmall", "remark",

    # === Counters for specific references ===
    "smallmbox", "smallmboxVG",
    "smileyface",  # mixed mode, tricky
}

# Macros to include in MathJax JavaScript config ONLY.
# These must NOT get do_cmd_* Perl wrappers or %mathjax_protected_cmds
# entries, because LaTeX2HTML has built-in text-mode handlers that we
# must not shadow.  (They're needed in MathJax for math-mode usage.)
MATHJAX_ONLY_SET = {
    "emph",          # l2h: <em>...</em>
    "ensuremath",    # l2h: passes through
    "index",         # l2h: index processing
    "sc",            # l2h: small-caps handling
    "textunderscore",  # l2h: literal underscore
    "texttilde",     # l2h: literal tilde
}


def extract_macros(filepath: Path) -> dict[str, tuple[int, str]]:
    """Extract macro definitions from a .tex file.

    Returns dict mapping macro_name -> (nargs, body).
    """
    text = filepath.read_text()
    macros: dict[str, tuple[int, str]] = {}

    # Remove comments (but not inside \mbox etc.)
    lines = []
    for line in text.split("\n"):
        # Skip lines inside \begin{htmlonly}...\end{htmlonly}
        stripped = line.lstrip()
        if stripped.startswith("%"):
            continue
        # Remove trailing comments (not preceded by \)
        cleaned = re.sub(r"(?<!\\)%.*$", "", line)
        lines.append(cleaned)
    text = "\n".join(lines)

    # Remove htmlonly blocks
    text = re.sub(
        r"\\begin\{htmlonly\}.*?\\end\{htmlonly\}",
        "",
        text,
        flags=re.DOTALL,
    )
    # Remove latexonly markers but keep content
    text = re.sub(r"%begin\{latexonly\}", "", text)
    text = re.sub(r"%end\{latexonly\}", "", text)
    text = re.sub(r"\\begin\{latexonly\}.*?\\end\{latexonly\}", "", text, flags=re.DOTALL)

    # Match \newcommand, \renewcommand, \providecommand, \def
    # Pattern for \newcommand{\name}[nargs]{body}
    pos = 0
    while pos < len(text):
        # Try \newcommand / \renewcommand / \providecommand
        m = re.match(
            r"\\(newcommand|renewcommand|providecommand)\s*\{\\(\w+)\}",
            text[pos:],
        )
        if m:
            cmd_type = m.group(1)
            name = m.group(2)
            pos += m.end()

            # Optional [nargs]
            nargs = 0
            m2 = re.match(r"\s*\[(\d+)\]", text[pos:])
            if m2:
                nargs = int(m2.group(1))
                pos += m2.end()

            # Optional [default] for optional arg — skip it
            m3 = re.match(r"\s*\[([^\]]*)\]", text[pos:])
            if m3:
                pos += m3.end()

            # Extract body in braces
            body, end = extract_braced(text, pos)
            if body is not None:
                pos = end
                if cmd_type == "providecommand":
                    if name not in macros:
                        macros[name] = (nargs, body)
                else:
                    macros[name] = (nargs, body)
            continue

        # Try \def\name{body} or \def\name#1#2{body}
        m = re.match(r"\\def\\(\w+)((?:#\d)*)", text[pos:])
        if m:
            name = m.group(1)
            params = m.group(2)
            nargs = params.count("#") if params else 0
            pos += m.end()
            body, end = extract_braced(text, pos)
            if body is not None:
                pos = end
                macros[name] = (nargs, body)
            continue

        # Try \DeclareMathOperator
        m = re.match(
            r"\\DeclareMathOperator\s*\{\\(\w+)\}\s*\{([^}]*)\}",
            text[pos:],
        )
        if m:
            name = m.group(1)
            body = f"\\operatorname{{{m.group(2)}}}"
            macros[name] = (0, body)
            pos += m.end()
            continue

        pos += 1

    return macros


def extract_braced(text: str, pos: int) -> tuple[str | None, int]:
    """Extract content inside balanced braces starting at pos.

    Skips whitespace before the opening brace.
    Returns (body, end_pos) or (None, pos) if no brace found.
    """
    # Skip whitespace
    while pos < len(text) and text[pos] in " \t\n\r":
        pos += 1

    if pos >= len(text) or text[pos] != "{":
        return None, pos

    depth = 0
    start = pos + 1
    i = pos
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            i += 2  # skip escaped char
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    return None, pos


def translate_body(body: str) -> str:
    """Translate LaTeX-isms in macro body to MathJax-compatible forms."""
    s = body

    # {\cal X} -> \mathcal{X}
    s = re.sub(r"\{\\cal\s+(\w)\}", r"\\mathcal{\1}", s)
    s = re.sub(r"\{\\cal\s+(\w+)\}", r"\\mathcal{\1}", s)

    # \hbox{\sc ...} and \mbox{\sc ...} -> \text{...} (combined)
    s = re.sub(r"\\hbox\s*\{\\sc\s+", r"\\text{", s)
    s = re.sub(r"\\mbox\s*\{\\sc\s+", r"\\text{", s)
    # \hbox{\small ...} and \mbox{\small ...} -> \text{...}
    s = re.sub(r"\\hbox\s*\{\\small\s+", r"\\text{", s)
    s = re.sub(r"\\mbox\s*\{\\small\s+", r"\\text{", s)
    # \hbox{\tiny ...} -> \text{...}
    s = re.sub(r"\\hbox\s*\{\\tiny\s+", r"\\text{", s)
    s = re.sub(r"\\mbox\s*\{\\tiny\s+", r"\\text{", s)
    # \hbox{\rm ...} -> \mathrm{...}
    s = re.sub(r"\\hbox\s*\{\\rm\s+", r"\\mathrm{", s)
    s = re.sub(r"\\mbox\s*\{\\rm\s+", r"\\mathrm{", s)
    # \hbox{...} and \mbox{...} -> \text{...}
    s = re.sub(r"\\hbox\s*\{", r"\\text{", s)
    s = re.sub(r"\\mbox\s*\{", r"\\text{", s)

    # {\bf X} -> \mathbf{X}  (single token)
    s = re.sub(r"\{\\bf\s+([^}]+)\}", r"\\mathbf{\1}", s)

    # {\rm X} -> \mathrm{X}
    s = re.sub(r"\{\\rm\s+([^}]+)\}", r"\\mathrm{\1}", s)

    # {\it X} -> \mathit{X}
    s = re.sub(r"\{\\it\s+([^}]+)\}", r"\\mathit{\1}", s)

    # {\sc ...} -> \text{...}
    s = re.sub(r"\{\\sc\s+([^}]+)\}", r"\\text{\1}", s)

    # \bm -> \boldsymbol, \pmb -> \boldsymbol, \mybm -> \boldsymbol
    s = re.sub(r"\\mybm\b", r"\\boldsymbol", s)
    s = re.sub(r"\\pmb\b", r"\\boldsymbol", s)
    # \bm only when used as command (not inside another word)
    s = re.sub(r"\\bm\b(?!\w)", r"\\boldsymbol", s)

    # \textbf{...} -> \mathbf{...} in math context
    s = re.sub(r"\\textbf\s*\{", r"\\mathbf{", s)

    # \textit{...} -> \mathit{...}
    s = re.sub(r"\\textit\s*\{", r"\\mathit{", s)

    # \textsc{...} -> \text{...}
    s = re.sub(r"\\textsc\s*\{", r"\\text{", s)

    # \textrm{...} -> \mathrm{...}
    s = re.sub(r"\\textrm\s*\{", r"\\mathrm{", s)

    # \texttt{...} -> \text{...}
    s = re.sub(r"\\texttt\s*\{", r"\\text{", s)

    # \fbox{$\displaystyle ...$} -> \boxed{...}
    s = re.sub(
        r"\\fbox\{\$\\displaystyle\s*(.*?)\$\}",
        r"\\boxed{\1}",
        s,
    )

    # \ensuremath{...} -> just the contents
    s = re.sub(r"\\ensuremath\s*\{", r"{", s)

    # \protect -> remove
    s = re.sub(r"\\protect\b\s*", "", s)

    # \nobreak -> remove
    s = re.sub(r"\\nobreak\b\s*", "", s)

    # Clean up spacing commands that MathJax handles differently
    # \, \; \! \quad etc. are fine in MathJax, keep them

    return s


def is_math_macro(name: str, body: str, nargs: int) -> bool:
    """Determine if a macro is math-mode (should be included)."""
    if name in EXCLUDE_SET:
        return False

    # Skip macros whose body references \begin{...} environments
    # (except array, which is math-mode)
    env_match = re.findall(r"\\begin\{(\w+)\}", body)
    for env in env_match:
        if env not in ("array",):
            return False

    # Skip macros whose body contains \section, \subsection, etc.
    if re.search(r"\\(section|subsection|subsubsection|chapter|paragraph)\b", body):
        return False

    # Skip macros that use \label, \ref, \pageref, \index, \cite
    if re.search(r"\\(label|ref|pageref|index|cite)\b", body):
        return False

    # Skip macros that use \htmladdnormallink or similar
    if "htmladdnormallink" in body or "htmlurl" in body:
        return False

    # Skip macros that use \footnote
    if "\\footnote" in body:
        return False

    # Skip macros with \message (debugging)
    if "\\message" in body:
        return False

    # Skip macros using \latex, \latexhtml, \html (conditional output)
    if re.search(r"\\(latex|latexhtml|html)\b", body):
        return False

    # Skip macros with \clearpage, \vspace, \hspace, \noindent, \bigskip, \raggedright
    if re.search(r"\\(clearpage|vspace|hspace|noindent|bigskip|raggedright|parskip|setlength)\b", body):
        return False

    # Skip macros using \input
    if "\\input" in body:
        return False

    # Skip empty macros that are just spacing/layout
    if body.strip() == "":
        return False

    # Skip macros with \par or \newline
    if re.search(r"\\(par|newline)\b", body):
        return False

    # Skip macros with \thanks
    if "\\thanks" in body:
        return False

    # Skip \makeindex, \makeatletter, etc.
    if re.search(r"\\make\w+", body):
        return False

    # Skip macros using \footnotetext
    if "\\footnotetext" in body:
        return False

    # Skip macros using tabular/table
    if re.search(r"\\begin\{(tabular|table|minipage|center|quote|list)\}", body):
        return False

    # Skip macros using \epsfbox, \epsfxsize, \includegraphics
    if re.search(r"\\(epsfbox|epsfxsize|includegraphics|leavevmode)\b", body):
        return False

    return True


def escape_for_perl(s: str) -> str:
    """Escape a string for embedding in a Perl single-quoted string."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def main() -> None:
    # Collect all macros from all files in order
    all_macros: dict[str, tuple[int, str]] = {}
    for f in SOURCE_FILES:
        if not f.exists():
            print(f"WARNING: {f} not found, skipping", file=sys.stderr)
            continue
        macros = extract_macros(f)
        for name, (nargs, body) in macros.items():
            # providecommand handled inside extract_macros
            all_macros[name] = (nargs, body)

    # Filter to math-mode macros
    math_macros: dict[str, tuple[int, str]] = {}
    for name, (nargs, body) in sorted(all_macros.items()):
        if is_math_macro(name, body, nargs):
            math_macros[name] = (nargs, translate_body(body))

    # Add supplementary built-in LaTeX commands needed by MathJax
    # (these aren't defined in style files but appear in math sources)
    SUPPLEMENTARY = {
        "sc": (1, "\\text{#1}"),           # small caps fallback
        "ensuremath": (1, "#1"),            # pass through in math mode
        "emph": (1, "\\textit{#1}"),        # emphasis
        "index": (1, ""),                   # consume argument, no output
    }
    for name, (nargs, body) in SUPPLEMENTARY.items():
        if name not in math_macros:
            math_macros[name] = (nargs, body)

    # Report
    print(f"Total macros extracted: {len(all_macros)}", file=sys.stderr)
    print(f"Math macros included:   {len(math_macros)}", file=sys.stderr)
    print(f"Excluded:               {len(all_macros) - len(math_macros)}", file=sys.stderr)

    # Generate Perl output
    lines: list[str] = []
    lines.append("# mathjax-macros.pl — AUTO-GENERATED by generate_mathjax_macros.py")
    lines.append("# DO NOT EDIT — regenerate with:")
    lines.append("#   python3 /w/jos-latex/tools/generate_mathjax_macros.py")
    lines.append("#")
    lines.append(f"# {len(math_macros)} math macros from {len(SOURCE_FILES)} style files")
    lines.append("")

    # %MATHJAX_MACROS hash
    lines.append("# MathJax macro definitions")
    lines.append("%MATHJAX_MACROS = (")
    for name in sorted(math_macros):
        nargs, body = math_macros[name]
        escaped = escape_for_perl(body)
        if nargs == 0:
            lines.append(f"    '{name}' => '{escaped}',")
        else:
            lines.append(f"    '{name}' => ['{escaped}', {nargs}],")
    lines.append(");")
    lines.append("")

    # %mathjax_protected_cmds hash
    # Skip MATHJAX_ONLY_SET: those must use l2h's built-in text-mode handlers
    lines.append("# Prevent l2h from expanding these via \\newcommand")
    lines.append("%mathjax_protected_cmds = (")
    for name in sorted(math_macros):
        if name not in MATHJAX_ONLY_SET:
            lines.append(f"    '{name}' => 1,")
    lines.append(");")
    lines.append("")

    # Helper functions
    lines.append("# ============================================================")
    lines.append("# MathJax pass-through helper functions")
    lines.append("# ============================================================")
    lines.append("")
    lines.append("# Helper: 0-arg MathJax passthrough")
    lines.append("sub _mathjax_pass0 {")
    lines.append("    my $cmd = shift; local($_) = @_;")
    lines.append('    return ($USE_MATHJAX ? "\\\\\\@#\\@\\@$cmd " : "") . $_;')
    lines.append("}")
    lines.append("")
    lines.append("# Helper: 1-arg MathJax passthrough")
    lines.append("sub _mathjax_pass1 {")
    lines.append("    my $cmd = shift; local($_) = @_;")
    lines.append("    if ($USE_MATHJAX) {")
    lines.append("        my $arg = '';")
    lines.append("        s/$next_pair_pr_rx/$arg = $2;''/eo")
    lines.append("            || s/$next_pair_rx/$arg = $2;''/eo")
    lines.append("            || ($arg = &missing_braces);")
    lines.append('        return "\\\\\\@#\\@\\@$cmd\\{$arg\\}" . $_;')
    lines.append("    }")
    lines.append("    $_;")
    lines.append("}")
    lines.append("")
    lines.append("# Helper: 2-arg MathJax passthrough")
    lines.append("sub _mathjax_pass2 {")
    lines.append("    my $cmd = shift; local($_) = @_;")
    lines.append("    if ($USE_MATHJAX) {")
    lines.append("        my ($a1, $a2) = ('', '');")
    lines.append("        s/$next_pair_pr_rx/$a1 = $2;''/eo")
    lines.append("            || s/$next_pair_rx/$a1 = $2;''/eo")
    lines.append("            || ($a1 = &missing_braces);")
    lines.append("        s/$next_pair_pr_rx/$a2 = $2;''/eo")
    lines.append("            || s/$next_pair_rx/$a2 = $2;''/eo")
    lines.append("            || ($a2 = &missing_braces);")
    lines.append('        return "\\\\\\@#\\@\\@$cmd\\{$a1\\}\\{$a2\\}" . $_;')
    lines.append("    }")
    lines.append("    $_;")
    lines.append("}")
    lines.append("")
    lines.append("# Helper: N-arg MathJax passthrough")
    lines.append("sub _mathjax_passN {")
    lines.append("    my $cmd = shift; my $n = shift; local($_) = @_;")
    lines.append("    if ($USE_MATHJAX) {")
    lines.append("        my @args;")
    lines.append("        for my $i (1..$n) {")
    lines.append("            my $arg = '';")
    lines.append("            s/$next_pair_pr_rx/$arg = $2;''/eo")
    lines.append("                || s/$next_pair_rx/$arg = $2;''/eo")
    lines.append("                || ($arg = &missing_braces);")
    lines.append("            push @args, $arg;")
    lines.append("        }")
    lines.append("        my $argstr = join('', map { \"\\{$_\\}\" } @args);")
    lines.append('        return "\\\\\\@#\\@\\@$cmd$argstr" . $_;')
    lines.append("    }")
    lines.append("    $_;")
    lines.append("}")
    lines.append("")

    # Generate do_cmd_* wrappers
    # Skip MATHJAX_ONLY_SET: those must use l2h's built-in text-mode handlers
    lines.append("# ============================================================")
    lines.append("# Compact do_cmd_* wrappers")
    lines.append("# ============================================================")
    lines.append("")
    for name in sorted(math_macros):
        if name in MATHJAX_ONLY_SET:
            continue
        nargs, body = math_macros[name]
        if nargs == 0:
            lines.append(
                f"sub do_cmd_{name} {{ _mathjax_pass0('{name}', @_) }}"
            )
        elif nargs == 1:
            lines.append(
                f"sub do_cmd_{name} {{ _mathjax_pass1('{name}', @_) }}"
            )
        elif nargs == 2:
            lines.append(
                f"sub do_cmd_{name} {{ _mathjax_pass2('{name}', @_) }}"
            )
        else:
            lines.append(
                f"sub do_cmd_{name} {{ _mathjax_passN('{name}', {nargs}, @_) }}"
            )
    lines.append("")
    lines.append("1;")
    lines.append("")

    OUTPUT.write_text("\n".join(lines))
    print(f"Wrote {OUTPUT}", file=sys.stderr)
    print(f"  {len(math_macros)} macros", file=sys.stderr)

    # Verify key macros are present
    key_macros = ["zi", "qv", "Amtx", "xv", "isdef", "zbox", "norm",
                  "twobytwo", "oper", "ip", "abs", "conj", "floor", "ceil"]
    missing = [m for m in key_macros if m not in math_macros]
    if missing:
        print(f"WARNING: Key macros missing: {missing}", file=sys.stderr)
    else:
        print("All key macros present.", file=sys.stderr)


if __name__ == "__main__":
    main()
