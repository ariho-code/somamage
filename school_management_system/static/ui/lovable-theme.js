// Lovable-style theme toggle (light/dark) with persistence
(function () {
  function getStoredTheme() {
    try {
      return localStorage.getItem("somamage-theme");
    } catch {
      return null;
    }
  }

  function setStoredTheme(theme) {
    try {
      localStorage.setItem("somamage-theme", theme);
    } catch {
      // ignore
    }
  }

  function applyTheme(theme) {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }

  function initTheme() {
    const stored = getStoredTheme();
    if (stored === "dark" || stored === "light") {
      applyTheme(stored);
      return;
    }

    // Default: follow OS preference
    const prefersDark =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(prefersDark ? "dark" : "light");
  }

  function toggleTheme() {
    const isDark = document.documentElement.classList.contains("dark");
    const next = isDark ? "light" : "dark";
    applyTheme(next);
    setStoredTheme(next);
  }

  // Expose for inline calls
  window.toggleSomaMangeTheme = toggleTheme;

  // Init ASAP
  initTheme();

  // Wire up button if present
  document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("themeToggle");
    if (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        toggleTheme();
      });
    }
  });
})();


