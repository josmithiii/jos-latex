# Exercise Audit Guide

How to audit a book's `course/data/exercises/<book>-exercises.json` for
**content correctness** — wrong answer keys, ambiguous options, false
statements in explanations/hints, authoring artifacts, and placement-rule
violations — then fix, commit, push, and verify the deployment.

Audience: the next agent (or human) auditing exercises for any of the four
books (mdft, filters, pasp, sasp). Companion to `ExercisesDeveloperGuide.md`
(in /w/mdft), which covers schema and placement for *authoring*; this guide
covers *auditing at scale*. Method proven on mdft (385 exercises, commit
8d32010) and filters (261, commit ddb02e1) in June 2026.

Track record to calibrate expectations: mdft yielded 13 content defects
(0 wrong answer keys); filters yielded 17, including **one wrong answer key,
one question with no correct option, and two leftover LLM-authoring
artifacts** ("Wait —", "Actually note...") inside explanations. The hw*
exercises (ported class problems) had the highest defect density.

---

## 0. Per-book facts

| Book | Math in exercise fields | HTML dir | Notes |
|------|------------------------|----------|-------|
| mdft | HTML entities ONLY (`&pi;`, `<sup>`, `<i>`) — HTML uses math images, no MathJax | mdftHTML/ | `\(...\)` would show as raw TeX |
| filters | MathJax `\(...\)` / `\[...\]` allowed, HTML entities also fine | filtersHTML/ | |
| pasp | MathJax allowed (HTML loads MathJax 3) | paspHTML/ | physical modeling conventions |
| sasp | MathJax allowed (HTML loads MathJax 3) | saspHTML/ | spectral/STFT conventions |

All four books: `validate-exercises.py` symlink at top level, course targets
via `$(JOS_LATEX)/Makefile.tex`, deploy with `make cw`.

The shared widget (`jos-latex/course/js/course-main.js`) typesets dynamically
inserted exercises with MathJax when available (added 2026-06-10), so MathJax
authoring is safe in the three MathJax books regardless of load-order races.

---

## 1. Phase 0 — structural + programmatic checks (cheap, do first)

```bash
cd /w/<book>
python3 validate-exercises.py --html-dir <book>HTML   # must pass before and after
```

Then in python, over every text field (question, options[].text,
explanation, hints[]):

1. **Authoring-artifact grep** — this caught 2 of the 4 filters criticals:
   `r'\bWait\b|\bActually\b|\bHmm\b|\bLet me\b|\bOops\b|TODO|FIXME'`
   Any hit is almost certainly a garbled explanation whose math should be
   re-derived from scratch, not patched.
2. **Math-format check** — for mdft only, flag `r'\\[a-zA-Z]+|\$[^$]+\$'`
   (raw LaTeX never renders there). For the MathJax books this is fine.
3. **Sanity** — `difficulty` an int in 1..5; answer-letter distribution
   (`Counter(e['correct'])`) not pathologically skewed per page.
4. **Overview-page heuristic** for the placement audit (§3): flag assigned
   pages whose HTML has a Child-Links table AND a body under ~250 words
   after stripping nav/child-links/scripts/tags. Expect mostly false
   positives — a short page that states the tested theorem is fine.

---

## 2. Phase 1 — parallel content audit

Slice the exercises array into chunks of **~38** and launch one
general-purpose subagent per chunk, all in parallel. Each agent prompt
should contain, in this order:

1. The file path and its exact python slice, e.g. `exercises[76:114]`.
2. The five checks, ranked: (a) is the marked `correct` option right?
   (b) is any OTHER option also defensibly correct? (c) explanation correct
   and consistent? (d) hints non-misleading? (e) question well-posed?
3. **A book-conventions block** (see §5) so agents don't flag the book's own
   conventions as errors.
4. The mandate: **verify numerically with python (numpy/scipy) whenever the
   claim is computable** — frequency responses, poles/zeros, filter outputs,
   DFTs, state-space transfer functions. Mental arithmetic is not evidence.
   For convention-dependent claims, grep the book's HTML page named by the
   exercise's `page` field and cite it.
5. The false-positive warning: report only genuine errors; if unsure, verify
   harder or omit.
6. Output contract: final message is parsed as data — return ONLY a JSON
   array `[{index, id, severity: critical|major|minor, issue, evidence,
   fix}]`, `[]` if clean.

Severity rubric: **critical** = wrong answer key, no correct option, or
garbled/self-contradicting explanation; **major** = second defensibly-correct
option (ambiguous), or false statement inside the correct option's text;
**minor** = wrong statement in explanation/hint/distractor-rationale, typo
that affects rendering, missing qualifier (e.g. "real" signal).

Classic defect patterns to prime agents with:
- A distractor **algebraically identical** to the correct answer
  (e.g. (z^N−1)/(z−1) vs (1−z^N)/(1−z); 2^N − x vs ~x+1).
- An "exact formula" distractor when the question asks "approximately" —
  the exact form is also correct → ambiguous.
- Off-by-one conditions stated inconsistently between option and explanation
  (N ≥ L1+L2 vs N ≥ L1+L2−1).
- Missing hypotheses (theorem needs x real / signal causal / a0 = 1).
- Notation contradicting the book's definition on the cited page (subscript
  conventions, 1/N factors, angle reference axes).
- Malformed HTML swallowing text (e.g. `</sub|}`).

## 3. Phase 2 — placement audit (one agent)

Give one agent: the placement rule and reading-order script from
`/w/mdft/ExercisesDeveloperGuide.md` §4 (adapt root file per book), the
heuristic-flagged page list from Phase 0, and ask for verdicts
`[{id, page, verdict: ok|move, target_page, reason}]`. Remind it that
material presented EARLIER in reading order satisfies the rule — only a
page strictly BEFORE its material is a violation. Apply only forward moves
to existing pages; `id` never changes on a move.

## 4. Phase 3 — verify, fix, validate, ship

1. **Independently re-verify every critical/major before applying** —
   especially answer-key flips and rewrites of the correct option. Rerun the
   numeric check yourself; for convention claims, read the cited book page
   yourself (strip tags, keep `IMG ALT` text — latex2html puts math there).
2. Back up: `cp <file>.json /tmp/<book>-exercises.json.bak`.
3. Apply fixes in ONE python script with a fail-fast helper:
   ```python
   def sub(e, field, old, new):
       assert old in e[field], f"{e['id']}.{field}: not found: {old[:60]!r}"
       e[field] = e[field].replace(old, new)
   ```
   Write back with `json.dump(d, f, indent=2, ensure_ascii=False)` plus a
   trailing newline (matches existing file style). Match each exercise's
   local notation style (entities vs MathJax) when writing replacement text.
4. Re-run `validate-exercises.py`, re-run the artifact grep, and review the
   full diff (`git diff -U0` on the JSON is readable — one line per field).
5. Commit (only the JSON; never `git commit -a`) with a message itemizing
   critical/major/minor by exercise id, and push.
6. Deploy: `make cw` in the book dir. Verify live:
   ```bash
   curl -s https://ccrma.stanford.edu/~jos/<book>/course/data/exercises/<book>-exercises.json \
     | diff -q - course/data/exercises/<book>-exercises.json
   ```
   For moved exercises, confirm the target page is live with the loader:
   `curl -s .../<page>.html | grep -c COURSE-INJECT` → 1.

Exercise progress in readers' localStorage is **not official** (JOS,
June 2026): answer-key flips and option rewrites need no migration concern,
but still keep `id`s stable out of habit.

---

## 5. Book-conventions blocks for agent prompts

**mdft** (Mathematics of the DFT): j = imaginary unit; DFT
X(k) = Σ_{n=0}^{N−1} x(n) e^{−j2πkn/N}, inverse has 1/N; frequencies in
rad/sample; text fields are inline HTML entities, never LaTeX.

**filters** (Introduction to Digital Filters): difference equation
y(n) = b0 x(n) + b1 x(n−1) + ... − a1 y(n−1) − a2 y(n−2) − ... (a-coeffs
with MINUS signs, a0 = 1); H(z) = B(z)/A(z); one-pole bandwidth
R = e^{−πBT}; state space x(n+1) = Ax + Bu, y = Cx + Du (controller
canonical: companion A, B = [1;0...], D from equal-degree division).

**pasp** (Physical Audio Signal Processing): digital waveguides — traveling
waves y = y^+ + y^−, wave impedance R0 = √(K/ε) (strings) or ρc/A (tubes);
force/velocity wave relations f^± = ±R0 v^±; scattering junctions
(Kelly-Lochbaum k = (R2−R1)/(R2+R1)); lossy/dispersive propagation filters;
FDNs and feedback matrices (lossless iff unitary-similar); bilinear-transform
digitizations of analog prototypes; commuted synthesis. Sampling interval T,
spatial step X = cT.

**sasp** (Spectral Audio Signal Processing): STFT X_m(ω_k) with hop R and
window w; COLA constraint Σ_m w(n−mR) = const; window transforms (main-lobe
widths in bins: rect 2, Hann 4, Hamming 4, Blackman 6); zero-phase vs causal
windowing; OLA vs FBS duality; spectral peak interpolation (quadratic in dB);
filter-bank views, weighted overlap-add. DFT/normalization conventions as
in mdft.

---

## 6. Cost calibration (June 2026 runs)

Per ~38-exercise audit agent: 45–90k subagent tokens, 1.5–6 min wall-clock,
all chunks in parallel. mdft (385 ex) = 10 agents + 1 placement; filters
(261) = 7 + 1. Expect pasp (724) ≈ 19 + 1 and sasp (518) ≈ 14 + 1.
Findings rate so far: ~4% of exercises need a fix; <1% critical.
