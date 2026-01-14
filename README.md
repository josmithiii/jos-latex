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
├── styles/               # LaTeX style files
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
