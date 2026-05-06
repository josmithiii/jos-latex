// MDFT Course Enhancement Loader
// Injected into each HTML page by inject-course.py
// Minimal footprint - just loads the course framework
(function() {
  'use strict';

  // Determine base URL based on host
  const isW3K = window.location.hostname.includes('w3k.org');
  const isCCRMA = window.location.hostname.includes('stanford.edu');
  const isLocal = window.location.hostname === 'localhost' ||
                  window.location.hostname === '127.0.0.1' ||
                  window.location.protocol === 'file:';

  // Derive a per-book short name (lowercase, e.g. "mdft", "sasp") from the URL
  // path: /~jos/mdft/foo.html -> "mdft". Used for per-book filenames and
  // localStorage keys so books don't share state. Books can override by
  // setting window.JOS_COURSE_NAME before this script runs.
  function deriveName() {
    if (typeof window.JOS_COURSE_NAME === 'string' && window.JOS_COURSE_NAME) {
      return window.JOS_COURSE_NAME;
    }
    const segments = window.location.pathname.split('/').filter(s => s && !/\.html?$/i.test(s));
    const book = segments[segments.length - 1];
    return book ? book.toLowerCase() : '';
  }
  const NAME = deriveName();

  // Base path for course assets
  let BASE;
  if (isLocal || isCCRMA) {
    // Relative path - course/ is sibling to HTML files
    BASE = 'course';
  } else if (isW3K) {
    // Full server-side support; per-book directory under /courses/
    BASE = `/courses/${NAME}/course`;
  } else {
    // Fallback to relative
    BASE = 'course';
  }

  // Load CSS
  const css = document.createElement('link');
  css.rel = 'stylesheet';
  css.href = BASE + '/css/course.css';
  document.head.appendChild(css);

  // Load main JS as module
  const js = document.createElement('script');
  js.src = BASE + '/js/course-main.js';
  js.type = 'module';

  // Derive a per-book title from the URL path. e.g. /~jos/mdft/foo.html -> "MDFT Course".
  // Books can override by setting window.JOS_COURSE_TITLE before this script runs.
  function deriveTitle() {
    if (typeof window.JOS_COURSE_TITLE === 'string' && window.JOS_COURSE_TITLE) {
      return window.JOS_COURSE_TITLE;
    }
    if (!NAME) return 'Course';
    return NAME.toUpperCase() + ' Course';
  }

  // Pass configuration to main script
  window.MDFT_COURSE_CONFIG = {
    base: BASE,
    isW3K: isW3K,
    isCCRMA: isCCRMA,
    isLocal: isLocal,
    page: window.location.pathname.split('/').pop() || 'index.html',
    NAME: NAME,
    title: deriveTitle()
  };

  // Wait for DOM ready before injecting
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      document.body.appendChild(js);
    });
  } else {
    document.body.appendChild(js);
  }
})();
