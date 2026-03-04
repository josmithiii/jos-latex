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
require "$_jl_dir/mathjax-macros.pl";

1;
