// SASP Course Enhancement - Main Entry Point
// Initializes all course features

const CONFIG = window.MDFT_COURSE_CONFIG || {
  base: 'course',
  isW3K: false,
  isCCRMA: false,
  isLocal: true,
  page: 'index.html'
};

class MDFTCourse {
  constructor() {
    this.sidebar = null;
    this.exercises = [];
    this.progress = this.loadProgress();
    this.currentPage = CONFIG.page;
    this.pageMetadata = null;
    this.allMetadata = null;
    this.isDarkMode = false;
  }

  async init() {
    console.log('SASP Course: Initializing...', CONFIG);

    // Fix viewport for iOS safe-area-insets
    this.fixViewportForIOS();

    // Detect dark mode from page
    this.detectDarkMode();

    // Load page metadata
    await this.loadPageMetadata();

    // Create sidebar
    this.createSidebar();

    // Load exercises for this page
    await this.loadExercises();

    // Load visualizations for this page
    await this.loadVisualizations();

    // Mark page as visited
    this.markPageVisited();

    // Add course-active class to body
    document.body.classList.add('course-active');

    console.log('SASP Course: Ready');
  }

  fixViewportForIOS() {
    // Update viewport meta tag to support safe-area-insets on iOS
    let viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
      const content = viewport.getAttribute('content') || '';
      if (!content.includes('viewport-fit')) {
        viewport.setAttribute('content', content + ', viewport-fit=cover');
      }
    } else {
      // Create viewport meta if it doesn't exist
      viewport = document.createElement('meta');
      viewport.name = 'viewport';
      viewport.content = 'width=device-width, initial-scale=1.0, viewport-fit=cover';
      document.head.appendChild(viewport);
    }

    // Discourage Safari Reader mode auto-activation
    // Reader mode strips JS/CSS, breaking course enhancements
    if (!document.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
      const webAppMeta = document.createElement('meta');
      webAppMeta.name = 'apple-mobile-web-app-capable';
      webAppMeta.content = 'yes';
      document.head.appendChild(webAppMeta);
    }
  }

  detectDarkMode() {
    // Check the page's background color to determine if we're in dark mode
    const bodyStyle = window.getComputedStyle(document.body);
    const bgColor = bodyStyle.backgroundColor;

    // Parse RGB values from background color
    const match = bgColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (match) {
      const r = parseInt(match[1]);
      const g = parseInt(match[2]);
      const b = parseInt(match[3]);

      // Calculate luminance (simple version)
      const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

      // If luminance is less than 0.5, it's a dark background
      this.isDarkMode = luminance < 0.5;
    } else {
      // Default to light mode if we can't parse
      this.isDarkMode = false;
    }

    // Add class to body so CSS variables apply to all course elements
    if (this.isDarkMode) {
      document.body.classList.add('course-dark-mode');
    }

    console.log('SASP Course: Dark mode detected:', this.isDarkMode);
  }

  createSidebar() {
    const sidebar = document.createElement('div');
    sidebar.className = 'course-sidebar';
    sidebar.innerHTML = `
      <button class="course-sidebar-toggle" aria-label="Toggle sidebar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 18l-6-6 6-6"/>
        </svg>
      </button>
      <div class="course-sidebar-header">
        <h3>SASP Course</h3>
      </div>
      <div class="course-sidebar-tabs">
        <button class="course-sidebar-tab active" data-tab="progress">Progress</button>
        <button class="course-sidebar-tab" data-tab="exercises">Exercises</button>
        <button class="course-sidebar-tab" data-tab="help">Help</button>
      </div>
      <div class="course-sidebar-content">
        <div class="course-tab-panel" data-panel="progress">
          ${this.renderProgressPanel()}
        </div>
        <div class="course-tab-panel" data-panel="exercises" style="display:none">
          <p style="color: var(--course-text-light)">Exercises for this page will appear here.</p>
        </div>
        <div class="course-tab-panel" data-panel="help" style="display:none">
          <div class="course-ai-help">
            <p style="margin-bottom: 12px;">Get AI help understanding this page:</p>
            <button class="course-ask-ai-btn" data-ai="claude">
              Ask Claude
            </button>
            <button class="course-ask-ai-btn" data-ai="chatgpt">
              Ask ChatGPT
            </button>
            <button class="course-ask-ai-btn" data-ai="gemini">
              Ask Gemini
            </button>
            <button class="course-ask-ai-btn" data-ai="perplexity">
              Ask Perplexity
            </button>
            <button class="course-ask-ai-btn" data-ai="grok">
              Ask Grok
            </button>
            <p class="course-ai-status" style="display:none; margin-top: 12px; font-size: 13px;"></p>
            <p style="margin-top: 16px; font-size: 12px; color: var(--course-text-light)">
              Copies page context to clipboard, then opens AI in new tab. Just paste!
            </p>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(sidebar);
    this.sidebar = sidebar;

    // Event listeners
    sidebar.querySelector('.course-sidebar-toggle').addEventListener('click', () => {
      this.toggleSidebar();
    });

    sidebar.querySelectorAll('.course-sidebar-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        this.switchTab(e.target.dataset.tab);
      });
    });

    // Load collapsed state
    if (localStorage.getItem('sasp-sidebar-collapsed') === 'true') {
      sidebar.classList.add('collapsed');
      document.body.classList.add('sidebar-collapsed');
    }

    // Bind reset progress button
    this.bindResetButton();

    // Bind Ask AI buttons
    this.bindAskAIButtons();
  }

  bindResetButton() {
    const resetBtn = this.sidebar.querySelector('.course-reset-progress');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetProgress());
    }
  }

  bindAskAIButtons() {
    this.sidebar.querySelectorAll('.course-ask-ai-btn').forEach(btn => {
      btn.addEventListener('click', () => this.askAI(btn.dataset.ai));
    });
  }

  extractPageContent() {
    // Get section title from first heading, stripping anchor junk
    const heading = document.querySelector('h1, h2');
    const title = heading?.textContent?.trim()?.replace(/\s+/g, ' ') || document.title;

    // Detect book title from the ADDRESS footer (latex2html convention:
    //   ``<A HREF="...">Book Title</A>'' by Author)
    const addressLink = document.querySelector('ADDRESS H5 A');
    const bookTitle = addressLink?.textContent?.trim() || CONFIG.bookTitle || document.title;

    // --- Extract main article body via innerHTML string surgery ---
    // This is more robust than DOM comment-node walking, which can fail
    // when browsers restructure the DOM during parsing.
    let html = document.body.innerHTML;

    // Strip comment-delimited regions (navigation panels, child-link TOCs)
    const stripRegion = (h, startMarker, endMarker) => {
      let result = h;
      while (true) {
        const s = result.indexOf(startMarker);
        if (s === -1) break;
        const e = result.indexOf(endMarker, s);
        if (e === -1) break;
        result = result.substring(0, s) + result.substring(e + endMarker.length);
      }
      return result;
    };
    html = stripRegion(html, '<!--Navigation Panel-->', '<!--End of Navigation Panel-->');
    html = stripRegion(html, '<!--Table of Child-Links-->', '<!--End of Table of Child-Links-->');

    // Parse the cleaned HTML into a detached container
    const container = document.createElement('div');
    container.innerHTML = html;

    // Remove remaining junk elements:
    // - ADDRESS: copyright/citation footer
    // - STRONG at top level that only contains nav links (safety net)
    // - HR: section separators
    // - script/style: code
    // - .course-sidebar: our own sidebar
    // - wz_tooltip.js creates hidden divs with id="tOoLtIp<N><N>"
    //   containing tooltip text for every onmouseover link on the page.
    //   These pollute textContent with "Click for ..." junk.
    container.querySelectorAll(
      'ADDRESS, script, style, hr, .course-sidebar, .navigation, ' +
      '[id^="tOoLtIp"], [id^="TTiEiFrM"]'
    ).forEach(el => el.remove());

    // Replace MathJax-rendered elements with original TeX source.
    // MathJax 3 (SVG or CHTML) wraps output in <mjx-container> and
    // stores the original TeX in a circular linked list at
    // MathJax.startup.document.math.list.  We collect TeX strings in
    // document order from the ORIGINAL page, then match them 1:1 with
    // <mjx-container> elements in our container (same order, since we
    // only removed non-math regions).
    if (window.MathJax && MathJax.startup && MathJax.startup.document) {
      const texSources = [];
      const sentinel = MathJax.startup.document.math.list;
      let node = sentinel.next;
      while (node !== sentinel && node.data) {
        if (node.data.math) {
          const d = node.data.display ? ['\\[', '\\]'] : ['\\(', '\\)'];
          texSources.push(d[0] + node.data.math + d[1]);
        }
        node = node.next;
      }
      const mjxEls = container.querySelectorAll('mjx-container');
      let ti = 0;
      mjxEls.forEach(mjx => {
        if (ti < texSources.length) {
          mjx.replaceWith(texSources[ti++]);
        }
      });
    }

    // Replace footnote links with a space (they point to footnode.html
    // and produce artifacts like "geometry.3.8Applying" in textContent).
    container.querySelectorAll('a[href*="footnode"]').forEach(el => {
      el.replaceWith(' ');
    });

    // Preserve paragraph structure: insert newlines around block elements
    // before extracting textContent (which otherwise collapses everything).
    container.querySelectorAll('p, div, br, h1, h2, h3, h4, h5, h6, li, tr, blockquote')
      .forEach(el => {
        el.insertAdjacentText('afterend', '\n');
        if (el.matches('h1, h2, h3, h4, h5, h6, p, div')) {
          el.insertAdjacentText('beforebegin', '\n');
        }
      });

    // Normalize custom JOS LaTeX macros and environments to standard
    // LaTeX so general-purpose LLMs can parse the math cleanly.
    // Macro definitions sourced from jos-latex/styles/.
    const normalizeTex = (s) => {
      let t = s;

      // --- Environment normalization ---
      // Strip environment wrappers (the outer \[...\] delimiters are
      // already provided by the MathJax TeX extraction step).
      t = t.replace(/\\begin\{equation\}([\s\S]*?)\\end\{equation\}/g,
        (_, body) => body.trim());
      // eqnarray/eqnarray*: strip environment AND & alignment markers
      t = t.replace(/\\begin\{eqnarray\*?\}([\s\S]*?)\\end\{eqnarray\*?\}/g,
        (_, body) => body.replace(/&/g, '').trim());

      // --- Mixed text-in-math cleanup ---
      // \hbox{...} and \mbox{...} → just the content
      t = t.replace(/\\[hm]box\{([^}]*)\}/g, '$1');

      // --- Custom macros ---
      // \zbox{...} → just the content (match balanced braces one level deep)
      t = t.replace(/\\zbox\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/g, '$1');
      // \reals, \complex, \CN
      t = t.replace(/\\reals\b/g, '\\mathbb{R}');
      t = t.replace(/\\complex\b/g, '\\mathbb{C}');
      t = t.replace(/\\CN\b/g, '\\mathbb{C}^N');
      // \isdef → ≜
      t = t.replace(/\\isdef\b/g, '\\triangleq');
      t = t.replace(/\\isdeftext\b/g, '\\triangleq');
      // \nnr → \\ (nonumber + newline in eqnarray)
      t = t.replace(/\\nnr\b/g, '\\\\');
      // \relop{X} → X (spacing wrapper)
      t = t.replace(/\\relop\{([^}]*)\}/g, '$1');
      // \elabel{...} → remove (internal cross-ref label)
      t = t.replace(/\\elabel\{[^}]*\}/g, '');
      // \ip{...} → \langle ... \rangle
      t = t.replace(/\\ip\{([^}]*)\}/g, '\\langle $1\\rangle');
      t = t.replace(/\\iptext\{([^}]*)\}/g, '\\langle $1\\rangle');
      // \conj{...} → \overline{...}
      t = t.replace(/\\conj\{([^}]*)\}/g, '\\overline{$1}');
      // \abs{...} → |...|
      t = t.replace(/\\abs\{([^}]*)\}/g, '\\left|$1\\right|');
      t = t.replace(/\\abstext\{([^}]*)\}/g, '|$1|');
      // Vectors: \xv, \uv, \vv
      t = t.replace(/\\xv\b/g, '\\underline{x}');
      t = t.replace(/\\uv\b/g, '\\underline{u}');
      t = t.replace(/\\vv\b/g, '\\underline{v}');
      // \Ts, \Fs
      t = t.replace(/\\Ts\b/g, 'T');
      t = t.replace(/\\Fs\b/g, 'f_s');
      // \projop
      t = t.replace(/\\projop\b/g, '\\mathbf{P}');
      // \Flip
      t = t.replace(/\\Flip\b/g, '\\operatorname{Flip}');
      // Clean up TeX spacing commands (replace with single space).
      // Use lookahead instead of \b since \qquad may abut text after
      // \hbox removal (e.g. "\qquadfor all" from "\qquad\hbox{for all}").
      t = t.replace(/\\qquad(?:\\!)?/g, ' ');
      t = t.replace(/\\quad(?!rature)/g, ' ');

      return t;
    };

    // Extract text and normalize whitespace while preserving line structure
    let text = container.textContent || '';
    text = normalizeTex(text);

    // Split multi-line display equations (\[...\] containing \\) into
    // separate \[...\] blocks.  This is safer for LLM parsing than \\
    // line breaks inside plain display math.
    text = text.replace(/\\\[([\s\S]*?)\\\]/g, (match, body) => {
      if (!body.includes('\\\\')) return match;
      return body.split('\\\\')
        .map(p => p.trim())
        .filter(p => p.length > 0)
        .map(p => '\\[' + p + '\\]')
        .join('\n\n');
    });

    text = text.replace(/[ \t]+/g, ' ');        // collapse horizontal whitespace
    text = text.replace(/\n[ \t]+/g, '\n');      // trim leading spaces on lines
    text = text.replace(/[ \t]+\n/g, '\n');      // trim trailing spaces on lines
    text = text.replace(/\n{3,}/g, '\n\n');      // max two consecutive newlines
    text = text.trim();

    // Truncate if too long (keep it reasonable for clipboard)
    const maxLen = 8000;
    if (text.length > maxLen) {
      text = text.substring(0, maxLen) + '\n... [truncated]';
    }

    return { title, text, bookTitle };
  }

  async askAI(provider) {
    const statusEl = this.sidebar.querySelector('.course-ai-status');
    const { title, text, bookTitle } = this.extractPageContent();

    // Build the prompt
    const prompt = `I'm studying "${bookTitle}" by Julius O. Smith III.

I'm currently reading the section: "${title}"

Here is the relevant content:

${text}

Please help me understand this material. You can:
- Explain concepts I'm confused about
- Work through examples
- Answer questions about the math
- Connect this to other topics in signal processing`;

    // Copy to clipboard
    try {
      await navigator.clipboard.writeText(prompt);
      statusEl.style.display = 'block';
      statusEl.style.color = 'var(--course-primary)';
      statusEl.textContent = 'Copied to clipboard! Paste in the AI chat.';
    } catch (err) {
      statusEl.style.display = 'block';
      statusEl.style.color = '#c00';
      statusEl.textContent = 'Could not copy. Try selecting and copying manually.';
      console.error('Clipboard error:', err);
      return;
    }

    // Brief delay so the system clipboard fully propagates before the
    // new tab reads it (some AI sites auto-read clipboard on load).
    await new Promise(r => setTimeout(r, 200));

    // Open AI in new tab
    const urls = {
      claude: 'https://claude.ai/new',
      chatgpt: 'https://chat.openai.com/',
      gemini: 'https://gemini.google.com/',
      perplexity: 'https://perplexity.ai/',
      grok: 'https://grok.com/'
    };

    window.open(urls[provider] || urls.claude, '_blank');
  }

  toggleSidebar() {
    const isCollapsed = this.sidebar.classList.toggle('collapsed');
    document.body.classList.toggle('sidebar-collapsed', isCollapsed);
    localStorage.setItem('sasp-sidebar-collapsed', isCollapsed);
  }

  switchTab(tabName) {
    this.sidebar.querySelectorAll('.course-sidebar-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === tabName);
    });
    this.sidebar.querySelectorAll('.course-tab-panel').forEach(p => {
      p.style.display = p.dataset.panel === tabName ? 'block' : 'none';
    });
  }

  getChapterStats() {
    if (!this.allMetadata) return null;

    const chapters = {};
    const backMatter = ['Bibliography', 'Index', 'About this document', 'Acknowledgments', 'Footnotes', 'Contents'];

    for (const [filename, meta] of Object.entries(this.allMetadata)) {
      const ch = meta.chapter || 'Other';
      const isBack = backMatter.some(bm => ch.includes(bm) || (meta.title && meta.title.includes(bm)));
      if (isBack) continue;

      if (!chapters[ch]) {
        chapters[ch] = { pages: [], totalTime: 0, visitedPages: 0 };
      }
      chapters[ch].pages.push(filename);
      chapters[ch].totalTime += meta.estimatedReadingMinutes || 0;
      if (this.progress.pagesVisited?.[filename]) {
        chapters[ch].visitedPages++;
      }
    }

    const chapterList = Object.entries(chapters)
      .filter(([name]) => name && name !== 'Other' && name !== 'Unknown')
      .sort((a, b) => b[1].totalTime - a[1].totalTime);

    const totalChapters = chapterList.length;
    const visitedChapters = chapterList.filter(([_, stats]) => stats.visitedPages > 0).length;
    const totalTime = chapterList.reduce((sum, [_, stats]) => sum + stats.totalTime, 0);

    return { chapters: chapterList, totalChapters, visitedChapters, totalTime };
  }

  renderProgressPanel() {
    const pagesVisited = Object.keys(this.progress.pagesVisited || {}).length;
    const totalPages = this.allMetadata ? Object.keys(this.allMetadata).length : 306;
    const percent = Math.round((pagesVisited / totalPages) * 100);

    const meta = this.pageMetadata;
    const readingTime = meta?.estimatedReadingMinutes;
    const chapter = meta?.chapter;
    const pageTitle = meta?.title || this.currentPage.replace(/_/g, ' ').replace('.html', '');

    // Get chapter-level stats
    const chapterStats = this.getChapterStats();
    const chapterProgress = chapterStats
      ? `${chapterStats.visitedChapters} of ${chapterStats.totalChapters} chapters started`
      : '';
    const totalHours = chapterStats ? Math.round(chapterStats.totalTime / 60) : 0;

    return `
      <div class="course-progress">
        <div class="course-progress-label">${chapterProgress}</div>
        <div class="course-progress-bar">
          <div class="course-progress-fill" style="width: ${chapterStats ? Math.round(chapterStats.visitedChapters / chapterStats.totalChapters * 100) : 0}%"></div>
        </div>
        <div style="margin-top: 4px; font-size: 11px; color: var(--course-text-light);">
          ${pagesVisited} of ${totalPages} pages visited${totalHours ? ` · ~${totalHours}h total content` : ''}
        </div>
      </div>
      <div style="margin-top: 16px;">
        <strong style="font-size: 13px;">Current Page</strong>
        <p style="margin-top: 4px; color: var(--course-text-light); font-size: 13px;">
          ${pageTitle}
        </p>
        ${chapter && chapter !== pageTitle ? `<p style="margin-top: 2px; color: var(--course-text-light); font-size: 12px; opacity: 0.7;">Chapter: ${chapter}</p>` : ''}
        ${readingTime ? `<p style="margin-top: 6px; color: var(--course-text-light); font-size: 12px;">~${readingTime} min read</p>` : ''}
      </div>
      <div style="margin-top: 16px;">
        <strong style="font-size: 13px;">Exercises Completed</strong>
        <p style="margin-top: 4px; color: var(--course-text-light); font-size: 13px;">
          ${Object.keys(this.progress.exercisesCompleted || {}).length} exercises
        </p>
      </div>
      <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--course-border);">
        <button class="course-reset-progress">Reset Progress</button>
      </div>
    `;
  }

  async loadExercises() {
    try {
      const response = await fetch(`${CONFIG.base}/data/exercises/sasp-exercises.json`);
      if (!response.ok) return;

      const data = await response.json();
      const pageExercises = data.exercises.filter(ex => ex.page === this.currentPage);

      if (pageExercises.length > 0) {
        this.exercises = pageExercises;
        this.injectExercises();
        this.updateExercisesTab();
      }
    } catch (e) {
      // Exercises not available yet - that's okay
      console.log('SASP Course: No exercises loaded', e.message);
    }
  }

  async loadPageMetadata() {
    try {
      const response = await fetch(`${CONFIG.base}/data/page-metadata.json`);
      if (!response.ok) return;

      this.allMetadata = await response.json();
      this.pageMetadata = this.allMetadata[this.currentPage] || null;

      if (this.pageMetadata) {
        console.log('SASP Course: Page metadata loaded', this.pageMetadata);
      }
    } catch (e) {
      console.log('SASP Course: No page metadata loaded', e.message);
    }
  }

  async loadVisualizations() {
    // Pages that should show the complex plane visualization
    const complexPlanePages = [
      'Complex_Plane.html',
      'Complex_Basics.html',
      'Euler_s_Identity.html',
      'Complex_Numbers.html',
      'Proof_Euler_s_Identity.html',
      'Vector_Interpretation_Complex_Numbers.html'
    ];

    if (!complexPlanePages.includes(this.currentPage)) {
      return;
    }

    try {
      // Load the visualization script
      await this.loadScript(`${CONFIG.base}/viz/complex-plane-embed.js`);

      // Find insertion point (after first major heading or intro paragraph)
      const h1 = document.querySelector('h1, h2');
      if (!h1) return;

      // Find a good spot - after the first paragraph following the heading
      let insertAfter = h1;
      let sibling = h1.nextElementSibling;
      while (sibling && (sibling.tagName === 'P' || sibling.tagName === 'DIV')) {
        insertAfter = sibling;
        sibling = sibling.nextElementSibling;
        // Stop after finding 2-3 paragraphs
        if (insertAfter.tagName === 'P') break;
      }

      // Create container and insert
      const container = document.createElement('div');
      container.className = 'course-viz-container';
      insertAfter.parentNode.insertBefore(container, insertAfter.nextSibling);

      // Initialize visualization
      new ComplexPlaneViz(container);
      console.log('SASP Course: Complex plane visualization loaded');

    } catch (e) {
      console.log('SASP Course: Could not load visualization', e.message);
    }
  }

  loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  injectExercises() {
    // Find the end of content (before the bottom navigation panel)
    const navPanels = document.querySelectorAll('hr');
    if (navPanels.length < 2) return;

    const insertPoint = navPanels[navPanels.length - 2];

    const container = document.createElement('div');
    container.className = 'course-exercises-container';
    container.innerHTML = `<h3 style="margin-top: 32px;">Check Your Understanding</h3>`;

    this.exercises.forEach((exercise, idx) => {
      container.appendChild(this.renderExercise(exercise, idx));
    });

    insertPoint.parentNode.insertBefore(container, insertPoint);
  }

  renderExercise(exercise, index) {
    const div = document.createElement('div');
    div.className = 'course-exercise';
    div.dataset.exerciseId = exercise.id;

    const optionsHtml = exercise.options.map((opt, i) => `
      <div class="course-exercise-option" data-option="${opt.id}">
        <div class="course-exercise-radio"></div>
        <div>${opt.text}</div>
      </div>
    `).join('');

    div.innerHTML = `
      <div class="course-exercise-header">
        <span class="course-exercise-badge">Exercise ${index + 1}</span>
        <span class="course-exercise-title">${exercise.type === 'multiple-choice' ? 'Multiple Choice' : exercise.type}</span>
      </div>
      <div class="course-exercise-question">${exercise.question}</div>
      <div class="course-exercise-options">${optionsHtml}</div>
      <div class="course-exercise-actions">
        <button class="course-btn course-btn-primary" data-action="check">Check Answer</button>
        <button class="course-btn course-btn-secondary" data-action="hint">Show Hint</button>
      </div>
      <div class="course-feedback"></div>
      <div class="course-hints">
        ${(exercise.hints || []).map((h, i) => `<div class="course-hint" data-hint="${i}">${h}</div>`).join('')}
      </div>
    `;

    // Event listeners
    div.querySelectorAll('.course-exercise-option').forEach(opt => {
      opt.addEventListener('click', () => {
        div.querySelectorAll('.course-exercise-option').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
      });
    });

    div.querySelector('[data-action="check"]').addEventListener('click', () => {
      this.checkAnswer(exercise, div);
    });

    div.querySelector('[data-action="hint"]').addEventListener('click', () => {
      this.showNextHint(div);
    });

    return div;
  }

  checkAnswer(exercise, div) {
    const selected = div.querySelector('.course-exercise-option.selected');
    if (!selected) {
      this.showFeedback(div, 'Please select an answer.', 'error');
      return;
    }

    const selectedId = selected.dataset.option;
    const isCorrect = selectedId === exercise.correct;

    // Update option styling
    div.querySelectorAll('.course-exercise-option').forEach(opt => {
      if (opt.dataset.option === exercise.correct) {
        opt.classList.add('correct');
      } else if (opt.classList.contains('selected')) {
        opt.classList.add('incorrect');
      }
    });

    if (isCorrect) {
      this.showFeedback(div, `Correct! ${exercise.explanation}`, 'success');
      this.markExerciseCompleted(exercise.id);
    } else {
      this.showFeedback(div, 'Not quite. Try again or use a hint.', 'error');
    }
  }

  showFeedback(div, message, type) {
    const feedback = div.querySelector('.course-feedback');
    feedback.textContent = message;
    feedback.className = `course-feedback visible ${type}`;
  }

  showNextHint(div) {
    const hints = div.querySelectorAll('.course-hint');
    for (const hint of hints) {
      if (!hint.classList.contains('visible')) {
        hint.classList.add('visible');
        return;
      }
    }
  }

  updateExercisesTab() {
    const panel = this.sidebar.querySelector('[data-panel="exercises"]');
    if (this.exercises.length > 0) {
      panel.innerHTML = `
        <p style="margin-bottom: 12px; color: var(--course-text-light);">
          ${this.exercises.length} exercise(s) for this page. Scroll down to try them!
        </p>
        ${this.exercises.map(ex => `
          <div style="padding: 8px; background: var(--course-bg); border-radius: 4px; margin-bottom: 8px;">
            <span style="font-size: 13px;">${ex.id}</span>
            ${this.progress.exercisesCompleted?.[ex.id] ? '<span style="color: var(--course-success);"> ✓</span>' : ''}
          </div>
        `).join('')}
      `;
    }
  }

  // Progress tracking
  loadProgress() {
    try {
      return JSON.parse(localStorage.getItem('sasp-progress') || '{}');
    } catch {
      return {};
    }
  }

  saveProgress() {
    localStorage.setItem('sasp-progress', JSON.stringify(this.progress));
  }

  markPageVisited() {
    if (!this.progress.pagesVisited) {
      this.progress.pagesVisited = {};
    }
    this.progress.pagesVisited[this.currentPage] = {
      lastVisit: new Date().toISOString(),
      visits: (this.progress.pagesVisited[this.currentPage]?.visits || 0) + 1
    };
    this.saveProgress();
  }

  markExerciseCompleted(exerciseId) {
    if (!this.progress.exercisesCompleted) {
      this.progress.exercisesCompleted = {};
    }
    if (!this.progress.exercisesCompleted[exerciseId]) {
      this.progress.exercisesCompleted[exerciseId] = {
        completedAt: new Date().toISOString()
      };
      this.saveProgress();
      this.updateExercisesTab();
      this.updateProgressPanel();
    }
  }

  updateProgressPanel() {
    const panel = this.sidebar.querySelector('[data-panel="progress"]');
    panel.innerHTML = this.renderProgressPanel();
    this.bindResetButton();
  }

  resetProgress() {
    if (confirm('Reset all progress? This will clear your page visits and exercise completions.')) {
      localStorage.removeItem('sasp-progress');
      this.progress = {};
      this.updateProgressPanel();
    }
  }
}

// Initialize on load
const course = new MDFTCourse();
course.init();
