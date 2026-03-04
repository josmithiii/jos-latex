# jos-latex

Shared LaTeX infrastructure for JOS textbooks.

## Overview

This repository contains the build system, LaTeX style files, tools, and shared resources needed to compile JOS textbooks:
- **mdft** - Mathematics of the Discrete Fourier Transform
- **filters** - Introduction to Digital Filters
- **pasp** - Physical Audio Signal Processing
- **sasp** - Spectral Audio Signal Processing

## Directory Structure

```
jos-latex/
├── Makefile.tex          # Master build rules (include from book Makefile)
├── styles/               # LaTeX style files and CSS
│   ├── jos.css           # Base CSS for HTML output
│   ├── stdcommon.tex     # Common packages and settings
│   ├── stddefs.tex       # Macro definitions
│   ├── stdmath.tex       # Math macros
│   ├── stdfigs-latex.tex # Figure macros (LaTeX)
│   ├── stdfigs-html.tex  # Figure macros (HTML)
│   └── mycaptionparlabel*.tex
├── tools/                # Build tools
│   ├── appdict           # Hyperlink injection tool
│   ├── localdict         # Dictionary preprocessor
│   ├── filterbbl         # BibTeX filter
│   └── ckc               # Character check
├── config/               # Configuration files
│   └── index-book.ist    # Index style
├── bib/                  # Bibliography
│   ├── jos.bib           # Master bibliography database
│   └── abbreviations-verbose.tex
└── dict/                 # Link dictionaries
    ├── open.dict         # Open dictionary
    └── realsimple.dict   # Simple dictionary
```

## Usage

### As a Git Submodule (Recommended)

```bash
# In your book repository:
git submodule add https://github.com/josmithiii/jos-latex.git

# Clone with submodules:
git clone --recurse-submodules https://github.com/josmithiii/mdft.git
```

### Book Makefile Setup

Create a Makefile in your book directory:

```makefile
NAME = mybook
OTHER_DEPENDS = *.tex eps/*.eps
JOS_LATEX = jos-latex

include $(JOS_LATEX)/Makefile.tex
```

### TEXINPUTS Setup

Add jos-latex/styles to your TEXINPUTS:

```bash
export TEXINPUTS=".:./jos-latex/styles//:"
export BIBINPUTS=".:./jos-latex/bib//:"
```

Or source the setup script:
```bash
source jos-latex/setup.sh
```

## Prerequisites

- TeX Live or MacTeX
- latex2html with MathJax support (l2hmj)

### Installing latex2html

```bash
git clone https://github.com/josmithiii/l2hmj.git
cd l2hmj && ./configure && make install
```

## MathJax

HTML output uses MathJax 3 with SVG rendering for correct math layout
across all browsers.  To enable MathJax in your project, add to your
`.latex2html-init`:

```perl
require "$initdir/jos-latex/l2h-mathjax-init.pl";
```

This sets `$USE_MATHJAX = 1`, loads macro definitions from your style
files, and configures SVG output with a global font cache.

## CSS Styling

The base stylesheet `styles/jos.css` is linked into every HTML build
automatically (`make html` creates a `jos.css` symlink in the book
directory).

### Customizing styles

To add project-specific CSS overrides on top of `jos.css`, set
`$EXTRA_STYLESHEET` in your project's `.latex2html-init` or `.l2h` file:

```perl
$EXTRA_STYLESHEET = "../mystyle.css";
```

This emits a second `<LINK>` tag after `jos.css`, so your rules take
precedence via normal CSS cascade.  No need to copy or modify `jos.css`.

To replace `jos.css` entirely, override `$STYLESHEET` instead:

```perl
$STYLESHEET = "../mystyle.css";
```

## Common Make Targets

| Target | Description |
|--------|-------------|
| `make pdf` | Build PDF via DVI and PS |
| `make po` | Build and open PDF |
| `make pb` | Print-ready PDF (grayscale, embedded fonts) |
| `make html` | Build HTML version |
| `make fresh` | Clean rebuild from scratch |
| `make help` | Show all targets |

## License

MIT License - see LICENSE file.

The build tools and infrastructure are freely available for any use.
Note: Individual books have their own licenses (typically CC BY-NC-ND 4.0).
