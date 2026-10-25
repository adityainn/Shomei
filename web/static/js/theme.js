/**
 * Shomei Theme Switcher (Light / Dark Mode)
 *
 * Centralized theme manager adhering to:
 * - Persistent preference via localStorage ('shomei_theme')
 * - Automatic fallback to system preference (prefers-color-scheme: dark)
 * - Anti-FOUC support via early execution
 * - Non-destructive: preserves active audit runs, selected cases, and findings
 * - Accessible aria-labels and keyboard focus
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'shomei_theme';

  function getSystemPreference() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  function getStoredPreference() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') {
        return stored;
      }
    } catch (e) {
      // Fallback silently if localStorage is restricted
    }
    return null;
  }

  function resolveCurrentTheme() {
    return getStoredPreference() || getSystemPreference();
  }

  function updateLogoImages(theme) {
    const logos = document.querySelectorAll('.site-logo-img');
    logos.forEach((img) => {
      if (theme === 'dark') {
        img.src = '/static/images/shomei_logo_dark.png';
      } else {
        img.src = '/static/images/shomei_logo.png';
      }
    });
  }

  function updateToggleButtons(theme) {
    const buttons = document.querySelectorAll('.theme-toggle-btn, #theme-toggle');
    const isDark = theme === 'dark';
    const label = isDark ? 'Switch to light mode' : 'Switch to dark mode';

    buttons.forEach((btn) => {
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
      btn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
    });
  }

  function applyTheme(theme, persist) {
    const validTheme = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', validTheme);

    if (persist) {
      try {
        localStorage.setItem(STORAGE_KEY, validTheme);
      } catch (e) {
        // Silently handle storage exceptions
      }
    }

    updateToggleButtons(validTheme);
    updateLogoImages(validTheme);

    // Notify canvas or other reactive components
    window.dispatchEvent(
      new CustomEvent('shomei:themechange', {
        detail: { theme: validTheme, isDark: validTheme === 'dark' }
      })
    );
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || resolveCurrentTheme();
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next, true);
  }

  // Apply resolved theme immediately
  const initialTheme = resolveCurrentTheme();
  document.documentElement.setAttribute('data-theme', initialTheme);

  // Wire controls once DOM is ready
  function initControls() {
    updateToggleButtons(document.documentElement.getAttribute('data-theme') || initialTheme);
    updateLogoImages(document.documentElement.getAttribute('data-theme') || initialTheme);

    // Event delegation for theme toggle buttons
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.theme-toggle-btn, #theme-toggle');
      if (btn) {
        e.preventDefault();
        toggleTheme();
      }
    });

    // Listen for system preference changes when no explicit override is saved
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e) => {
        if (!getStoredPreference()) {
          applyTheme(e.matches ? 'dark' : 'light', false);
        }
      };

      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleChange);
      } else if (mediaQuery.addListener) {
        mediaQuery.addListener(handleChange);
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initControls);
  } else {
    initControls();
  }

  // Expose global API
  window.ShomeiTheme = {
    getTheme: () => document.documentElement.getAttribute('data-theme') || resolveCurrentTheme(),
    applyTheme: (t) => applyTheme(t, true),
    toggleTheme: toggleTheme,
    resetToSystem: () => {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch (e) {}
      applyTheme(getSystemPreference(), false);
    }
  };
})();
