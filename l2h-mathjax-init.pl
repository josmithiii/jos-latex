# l2h-mathjax-init.pl — MathJax setup for latex2html
# Shared across JOS projects via the jos-latex submodule.
#
# Usage: In your project's dot-latex2html-init, add:
#   require "$initdir/jos-latex/l2h-mathjax-init.pl";
# where $initdir is the project root (already set in dot-latex2html-init).

use File::Basename;
use Cwd qw(abs_path);
my $_jl_dir = dirname(abs_path(__FILE__));

$USE_MATHJAX = 1;
$MATHJAX_EXTERNAL_CONFIG = 1;  # write shared mathjax-config.js; browser caches it across pages
require "$_jl_dir/mathjax-macros.pl";

# Expand environment-abbreviation macros from stddefs.tex before
# latex2html's environment parser runs (fixes long-standing l2h issue
# noted in stddefs.tex line 143: "l2h gets fouled up on \BIT").
# Uses the pre_pre_process hook called at the top of pre_process().
sub pre_pre_process {
    s/\\BIT\b/\\begin{itemize}/g;
    s/\\EIT\b/\\end{itemize}/g;
    s/\\bit\b/\\begin{itemize}/g;
    s/\\eit\b/\\end{itemize}/g;
    s/\\BNUM\b/\\begin{enumerate}/g;
    s/\\ENUM\b/\\end{enumerate}/g;
    s/\\bnum\b/\\begin{enumerate}/g;
    s/\\enum\b/\\end{enumerate}/g;
    s/\\BITC\b/\\begin{itemize}/g;
    s/\\EITC\b/\\end{itemize}/g;
    s/\\BNUMC\b/\\begin{enumerate}/g;
    s/\\ENUMC\b/\\end{enumerate}/g;
}

1;
