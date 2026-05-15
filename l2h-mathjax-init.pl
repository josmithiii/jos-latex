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

# Undo l2hconf.pm's image-mode registration of text-mode commands that
# have native do_cmd_* handlers in mathjax-macros.pl.  l2hconf.pm is
# loaded by `use l2hconf` very early in latex2html -- well before this
# init file -- and registers e.g. \fbox via process_commands_in_tex,
# creating a wrap_cmd_fbox that latex2html's wrap_raw_arg_cmds then
# dispatches to in preference to do_cmd_fbox.  That wraps \fbox{...}
# in a tex2html_wrap environment, which (in MathJax mode) emerges as
# `\(\fbox{...}\)` and fails when the contents include text-mode
# constructs MathJax cannot parse (\begin{tabular}, etc).  Removing
# wrap_cmd_fbox and the raw_arg_cmds entry lets \fbox fall through to
# normal translate_commands dispatch and reach do_cmd_fbox.
for my $cmd ('fbox') {
    next unless (defined &{"main::do_cmd_$cmd"});
    undef &{"main::wrap_cmd_$cmd"} if (defined &{"main::wrap_cmd_$cmd"});
    delete $main::raw_arg_cmds{$cmd};
}

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

# NOTE: Earlier versions of this file defined do_cmd_ccrmahomepage and
# do_cmd_josemail to render those macros for HTML output. They were
# removed because they conflict with the \newcommand definitions in
# jos-latex/styles/stddefs.tex: latex2html warns "previous meaning will
# be lost" and then renders neither the perl handler nor the \newcommand
# expansion, producing the garbled "Julius O. Smith IIIjos" on title
# pages and an empty rendering for \josemail. The stddefs.tex
# \newcommand definitions handle both PDF and HTML output on their own.

1;
