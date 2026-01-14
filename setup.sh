#!/bin/bash
# Source this file to set up environment for building JOS books
# Usage: source jos-latex/setup.sh

# Get the directory where this script lives
JOS_LATEX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set TEXINPUTS to find style files
export TEXINPUTS=".:${JOS_LATEX_DIR}/styles//:${TEXINPUTS}"

# Set BIBINPUTS for bibliography
export BIBINPUTS=".:${JOS_LATEX_DIR}/bib//:${BIBINPUTS}"

# Set BSTINPUTS for bibliography styles
export BSTINPUTS=".:${JOS_LATEX_DIR}/bib//:${BSTINPUTS}"

echo "JOS LaTeX environment configured:"
echo "  TEXINPUTS includes: ${JOS_LATEX_DIR}/styles//"
echo "  BIBINPUTS includes: ${JOS_LATEX_DIR}/bib//"
