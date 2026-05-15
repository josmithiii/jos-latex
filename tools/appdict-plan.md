# appdict — rewrite plan (parked)

Written 2026-05-15 after the inline-tag matching fix (jos-latex commit
`9138bcd`). Captured here so the analysis isn't lost; not a commitment
to do the rewrite now.

## Current state

`appdict` (Perl) works. The recent fix makes it match keys across
transparent inline tags like `<I>z</I> transform`. For the code paths
currently exercised, it is solidly fine. If nothing else breaks, leave
it alone.

## Why it's not "smooth swimming" though

The rough edges hit while making the recent fix:

- **Fighting HTML::Parser's streaming model.** Pass 2 emits text in
  chunks split at every tag boundary. Making keys match across inline
  markup required adding ~100 lines of event buffering + offset
  arithmetic on top of an already-dense state machine (`$skipping`,
  `$in_math`, `&&&MATCH-TAG-$m-&&&` placeholder substitution). Every
  new edge case will need similar surgery.
- **dutil.pm overhead.** ~500 lines of Perl that parse the `.dict`
  format and maintain a `.dictpc` precompiled cache using `!` as a
  record separator, with bespoke handling for entities, escapes, and
  NULL sentinels. Inherited as part of any future maintenance.
- **Historical scar tissue.** Plenty of `FIXME` / `PROBLEM` /
  `MAYBE NEED TO` comments documenting things that bit past-jos.
- **Perl runtime fragility.** Shebang is `#!/usr/bin/perl -w` (Apple
  system Perl 5.34); one required module (`HTML::Entities`) is missing
  under the MacPorts Perl. Apple has been threatening to remove system
  Perl for years; when it disappears, this is a forced port.

## Proposed replacement

Concrete and bounded:

- **Python 3 + `lxml`** (or BeautifulSoup with the lxml backend).
  Tree-walking sees "text of this `<td>` is `<I>z</I> transform`" as
  one unit -- no buffer-and-splice gymnastics. "Skip inside
  `<a>/<h1>/script/style/MATH`" becomes a one-line ancestor check.
- **Drop `.dictpc`.** A 250 kB `.dict` parses in tens of ms in Python;
  the cache solves a problem that no longer exists. Deletes ~150 lines
  of dutil.
- **Keep the `.dict` text format.** Years of hand-curated content lives
  in it; no reason to disturb that.
- **Keep the CLI signature**
  `appdict dict1.dict … infile.html outfile.html` so the Makefile rule
  is a one-line swap and old vs new can run side-by-side.
- **Pin to ~400 lines + a pytest file** that diffs the new output
  against the current `appdict` output on `galleyHTML/*.html`. Done
  when `diff -u` is empty (or contains only intended changes).

## Sizing

A day for a working translation, plus a second day for the
"diff against old output until they match" loop. Not a weekend
project but not a quarter either.

## Recommended trigger

Rewrite the *next* time appdict bites, not pre-emptively. Two reasons:

1. Right now it's freshly fixed, so urgency is at its low point.
2. The next bug will tell us which corner of the spec actually matters
   in 2026, and we can let that constrain the rewrite rather than
   trying to preserve every quirk of the 2001 code.

## Behaviors to preserve (spec checklist for the rewrite)

From reading the current implementation:

- Multiple input dictionaries, processed in order
- Per-key `DEF`, `URL` fields; synonym groups in a single `KEY` line via `|`
- `URL = ?` → Google search URL synthesized from the matched phrase
- `URL = search` → freefind site-search URL
- `DEF` may contain HTML entities; HTML-encode before injection into
  the `onMouseover` attribute
- Word-stem tolerance: trailing `s`, `es`, `ed`, `ing`, `'s` variants
- Hyphen / underscore tolerated as inter-word separator
- Bare URLs in the page text auto-link to themselves
- Skip inside `<a>`, `<h1>`, `<title>`, `<script>`, `<style>`,
  `<nolinks>`
- Skip inside MathJax (any element with `class="MATH"` or
  `class="MATHDISPLAY"`)
- `firstonly` mode (default) vs all-occurrences (used for Bibliography)
- Don't self-link: skip keys whose URL points at the current file
- `-bibfile` option (currently noted but not fully wired)
- Output: wrap matched text in
  `<A HREF="<url>" onMouseover="return escape('<def>')">…</A>`
- Cleanly nest around inline markup: produce `<A>…<I>z</I></A>`, not
  `<A>…<I>z</A></I>`; place opens after non-transparent block-level
  start tags (`<A>` inside `<TD>`, not wrapping it)

## Test corpus

`/Users/jos/w/filters/galleyHTML/*.html` plus
`/Users/jos/w/filters/filtersHTML/*.html` give thousands of pages of
real-world input. Pin the diff against the current output and the
rewrite is well-constrained.
