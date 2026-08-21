#!/usr/bin/env node
/**
 * mathjax-check.js -- find every math expression in a latex2html+MathJax
 * HTML tree that the browser would render as an error (red text).
 *
 * It loads the tree's own mathjax-config.js (macros, delimiters, packages)
 * and parses each page with the real MathJax 3 TeX input jax, exactly as
 * the browser does, with two deliberate differences:
 *
 *   - the `noundefined` package is left out, so an undefined control
 *     sequence (e.g. a document macro such as \xvnu that latex2html failed
 *     to substitute) is REPORTED instead of being silently typeset in red;
 *   - the `autoload` package is left out, so a command the browser would
 *     fetch from the CDN on demand (\cancel, \color, \boldsymbol, ...) is
 *     reported as AUTOLOAD: preload it via @MATHJAX_PACKAGES in
 *     jos-latex/l2h-mathjax-init.pl (see the comment there for why the
 *     on-demand fetch is a race that can leave the command unexpanded).
 *
 * Every other MathJax parse error (missing braces, misplaced &, unknown
 * environment, \begin{tabular} inside math, ...) is reported too.
 *
 * Usage:
 *     node mathjax-check.js [--verbose] [--summary] HTMLDIR
 *
 * Setup (once):  cd jos-latex/tools && npm ci
 *
 * Exit status: 0 clean, 1 problems found, 2 usage/setup error.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

function die(msg) {
  console.error(`*** mathjax-check: ${msg}`);
  process.exit(2);
}

let mj;
let parse5;
try {
  parse5 = require('parse5');
  mj = {
    mathjax: require('mathjax-full/js/mathjax.js').mathjax,
    TeX: require('mathjax-full/js/input/tex.js').TeX,
    liteAdaptor: require('mathjax-full/js/adaptors/liteAdaptor.js').liteAdaptor,
    RegisterHTMLHandler: require('mathjax-full/js/handlers/html.js').RegisterHTMLHandler,
    ConfigurationHandler: require('mathjax-full/js/input/tex/Configuration.js').ConfigurationHandler,
    AutoloadConfiguration:
      require('mathjax-full/js/input/tex/autoload/AutoloadConfiguration.js').AutoloadConfiguration,
  };
  // Registers every TeX extension shipped with mathjax-full so that any
  // package named in the tree's config (or in the autoload table) resolves.
  require('mathjax-full/js/input/tex/AllPackages.js');
} catch (e) {
  die(`mathjax-full/parse5 not installed -- run "npm ci" in ${__dirname}\n    (${e.message})`);
}

// ---------------------------------------------------------------- CLI
const argv = process.argv.slice(2);
let verbose = false;
let summaryOnly = false;
let dir = null;
for (const a of argv) {
  if (a === '--verbose' || a === '-v') verbose = true;
  else if (a === '--summary') summaryOnly = true;
  else if (a.startsWith('-')) die(`unknown option ${a}`);
  else if (dir === null) dir = a;
  else die('only one HTMLDIR may be given');
}
if (dir === null) die('usage: node mathjax-check.js [--verbose] [--summary] HTMLDIR');
if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) die(`not a directory: ${dir}`);

const files = fs.readdirSync(dir)
  .filter((f) => f.toLowerCase().endsWith('.html'))
  .sort()
  .map((f) => path.join(dir, f));
if (files.length === 0) die(`no *.html files in ${dir}`);

// --------------------------------------------------------- MathJax config
// The browser's default TeX package set (MathJax 3 tex-* combined builds).
const BROWSER_DEFAULT_PACKAGES =
  ['base', 'ams', 'newcommand', 'require', 'autoload', 'noundefined', 'configmacros'];
// Packages that exist only in the browser build, or that we deliberately
// drop so that problems surface as errors (see file header).
const DROP_PACKAGES = new Set(['require', 'autoload', 'noundefined']);

function loadConfig() {
  const cfgPath = path.join(dir, 'mathjax-config.js');
  let src;
  let where;
  if (fs.existsSync(cfgPath)) {
    src = fs.readFileSync(cfgPath, 'utf8');
    where = cfgPath;
  } else {
    // $MATHJAX_EXTERNAL_CONFIG = 0: the config is inlined in every page.
    const html = fs.readFileSync(files[0], 'utf8');
    const m = html.match(/<script>\s*(window\.MathJax\s*=\s*\{[\s\S]*?\})\s*;?\s*<\/script>/);
    if (!m) die(`no mathjax-config.js in ${dir} and no inline window.MathJax config in ${files[0]}`);
    src = m[1];
    where = files[0];
  }
  const sandbox = { window: {} };
  try {
    vm.runInNewContext(src, sandbox, { filename: where });
  } catch (e) {
    die(`cannot evaluate MathJax config ${where}: ${e.message}`);
  }
  const cfg = sandbox.window.MathJax;
  if (!cfg || typeof cfg.tex !== 'object') die(`${where} did not define window.MathJax.tex`);
  return { cfg, where };
}

function resolvePackages(texCfg) {
  const pk = texCfg.packages;
  let list;
  if (Array.isArray(pk)) list = pk.slice();
  else if (pk && Array.isArray(pk['[+]'])) list = BROWSER_DEFAULT_PACKAGES.concat(pk['[+]']);
  else if (pk === undefined) list = BROWSER_DEFAULT_PACKAGES.slice();
  else die(`unsupported tex.packages form in config: ${JSON.stringify(pk)}`);
  if (pk && Array.isArray(pk['[-]'])) list = list.filter((p) => !pk['[-]'].includes(p));
  list = [...new Set(list)].filter((p) => !DROP_PACKAGES.has(p));
  for (const p of list) {
    if (!mj.ConfigurationHandler.get(p)) die(`TeX package "${p}" (from config) is unknown to mathjax-full`);
  }
  return list;
}

// cmd -> package and env -> package, from MathJax's own autoload table.
const autoloadCmd = new Map();
const autoloadEnv = new Map();
{
  const table = mj.AutoloadConfiguration.options.autoload;
  for (const pkg of Object.keys(table)) {
    const entry = table[pkg];
    const [cmds, envs] = Array.isArray(entry[0]) ? entry : [entry, []];
    for (const c of cmds) autoloadCmd.set(c, pkg);
    for (const e of envs) autoloadEnv.set(e, pkg);
  }
}

const { cfg, where: cfgWhere } = loadConfig();
const texCfg = cfg.tex;
const packages = resolvePackages(texCfg);
const macros = texCfg.macros || {};

mj.RegisterHTMLHandler(mj.liteAdaptor());

// ---------------------------------------------------------------- scan
let errors = []; // filled by formatError for the page being compiled

const texOptions = {
  packages,
  macros,
  inlineMath: texCfg.inlineMath || [['\\(', '\\)']],
  displayMath: texCfg.displayMath || [['$$', '$$'], ['\\[', '\\]']],
  processEscapes: texCfg.processEscapes !== undefined ? texCfg.processEscapes : true,
  processEnvironments: texCfg.processEnvironments !== undefined ? texCfg.processEnvironments : true,
  processRefs: texCfg.processRefs !== undefined ? texCfg.processRefs : true,
  tags: texCfg.tags || 'none',
  formatError: (jax, err) => {
    errors.push({ message: err.message, id: err.id, latex: jax.latex });
    return jax.formatError(err);
  },
};

function htmlEscape(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function lineOf(html, latex) {
  let i = html.indexOf(latex);
  if (i < 0) i = html.indexOf(htmlEscape(latex));
  if (i < 0) return '?';
  return String(html.slice(0, i).split('\n').length);
}

function classify(err) {
  let m = err.message.match(/^Undefined control sequence \\(\S+)/);
  if (m) {
    const pkg = autoloadCmd.get(m[1]);
    return pkg
      ? { kind: 'AUTOLOAD', key: `\\${m[1]} needs [tex]/${pkg} in @MATHJAX_PACKAGES` }
      : { kind: 'UNDEFINED', key: `\\${m[1]}` };
  }
  m = err.message.match(/^Unknown environment '([^']+)'/);
  if (m) {
    const pkg = autoloadEnv.get(m[1]);
    return pkg
      ? { kind: 'AUTOLOAD', key: `{${m[1]}} needs [tex]/${pkg} in @MATHJAX_PACKAGES` }
      : { kind: 'UNKNOWN-ENV', key: `{${m[1]}}` };
  }
  return { kind: 'PARSE', key: err.message };
}

function snippet(latex) {
  const s = latex.replace(/\s+/g, ' ').trim();
  return s.length > 110 ? `${s.slice(0, 107)}...` : s;
}

const tally = new Map(); // `${kind}  ${key}` -> count
let total = 0;
let badFiles = 0;
let mathCount = 0;

// Document-level options the browser honours (which tags/classes to skip).
const docOptions = {};
for (const k of ['skipHtmlTags', 'includeHtmlTags', 'ignoreHtmlClass', 'processHtmlClass']) {
  if (cfg.options && cfg.options[k] !== undefined) docOptions[k] = cfg.options[k];
}

// MathJax's lite DOM parser is not a browser: it is case-sensitive about
// tag names (latex2html emits <TITLE>...</TITLE>, <SPAN CLASS="MATH">;
// an unmatched </TITLE> swallows the rest of the page as text) and it
// crashes on a stray closing tag (</BLOCKQUOTE></BLOCKQUOTE>).  Build
// the DOM the way a browser would, with an HTML5 parser, and hand MathJax
// the serialised result.
function normalizeHtml(html) {
  return parse5.serialize(parse5.parse(html));
}

for (const file of files) {
  const html = fs.readFileSync(file, 'utf8');
  errors = [];
  // Fresh input jax per page: tag/label state (tags: 'ams') is per page in
  // the browser as well.
  const tex = new mj.TeX(texOptions);
  let doc;
  try {
    doc = mj.mathjax.document(normalizeHtml(html), { InputJax: tex, ...docOptions });
    doc.findMath();
  } catch (e) {
    die(`MathJax could not process ${file} (${html.length} bytes): ${e.message}`);
  }
  for (const _ of doc.math) mathCount += 1; // doc.math is a linked list
  doc.compile();

  if (errors.length) badFiles += 1;
  else if (verbose) console.log(`  ${path.basename(file)}: clean`);

  for (const err of errors) {
    total += 1;
    const { kind, key } = classify(err);
    const tkey = `${kind}  ${key}`;
    tally.set(tkey, (tally.get(tkey) || 0) + 1);
    if (!summaryOnly) {
      console.log(`${file}:${lineOf(html, err.latex)}: [${kind}] ${err.message}  ::  ${snippet(err.latex)}`);
    }
  }
}

// ------------------------------------------------------------- summary
if (total) {
  console.log('');
  console.log('mathjax-check: problems by kind / command (count):');
  const rows = [...tally.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  for (const [k, n] of rows) console.log(`  ${String(n).padStart(5)}  ${k}`);
  console.error(
    `\nmathjax-check: FAIL -- ${total} MathJax error(s) in ${badFiles}/${files.length} file(s)` +
    ` (${mathCount} expressions; config ${cfgWhere}; packages ${packages.join(',')})`,
  );
  process.exit(1);
}
console.log(
  `mathjax-check: OK -- ${files.length} file(s), ${mathCount} expressions parsed cleanly` +
  ` (config ${cfgWhere}; packages ${packages.join(',')})`,
);
