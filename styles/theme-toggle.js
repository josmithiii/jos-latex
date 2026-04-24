(function () {
    var STORAGE_KEY = 'jos-theme';
    var mediaQuery = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');

    function storedTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            return null;
        }
    }

    function systemTheme() {
        return mediaQuery && mediaQuery.matches ? 'dark' : 'light';
    }

    function activeTheme() {
        var theme = storedTheme();
        return theme === 'light' || theme === 'dark' ? theme : systemTheme();
    }

    function setStoredTheme(theme) {
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (error) {
        }
        document.documentElement.setAttribute('data-theme', theme);
    }

    function install() {
        if (document.getElementById('themeToggle') || !document.body) {
            return;
        }
        var button = document.createElement('button');
        button.type = 'button';
        button.id = 'themeToggle';
        button.className = 'theme-toggle';
        document.body.insertBefore(button, document.body.firstChild);

        function updateButton() {
            var theme = activeTheme();
            button.innerHTML = theme === 'dark'
                ? '&#x2192;<span class="sun">&#x2600;&#xFE0E;</span>'
                : '&#x2192;<span class="moon">&#x263E;</span>';
            var label = theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
            button.setAttribute('aria-label', label);
            button.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
        }

        button.addEventListener('click', function () {
            setStoredTheme(activeTheme() === 'dark' ? 'light' : 'dark');
            updateButton();
        });

        if (mediaQuery && mediaQuery.addEventListener) {
            mediaQuery.addEventListener('change', function () {
                if (!storedTheme()) {
                    updateButton();
                }
            });
        }

        updateButton();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', install);
    } else {
        install();
    }
}());
