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

  // Base path for course assets
  let BASE;
  if (isLocal || isCCRMA) {
    // Relative path - course/ is sibling to HTML files
    BASE = 'course';
  } else if (isW3K) {
    // Full server-side support
    BASE = '/courses/mdft/course';
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

  // Pass configuration to main script
  window.MDFT_COURSE_CONFIG = {
    base: BASE,
    isW3K: isW3K,
    isCCRMA: isCCRMA,
    isLocal: isLocal,
    page: window.location.pathname.split('/').pop() || 'index.html'
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
