// Professional UI interactions (keeps backend untouched)
(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }
  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  // Mark active sidebar link based on URL
  function setActiveSidebarLink() {
    const nav = qs(".sidebar-menu");
    if (!nav) return;
    const links = qsa("a[href]", nav).filter((a) => a.getAttribute("href") !== "#");

    const currentPath = window.location.pathname || "/";
    let best = null;
    let bestLen = -1;

    links.forEach((a) => {
      try {
        const url = new URL(a.href, window.location.origin);
        const p = url.pathname;
        if (p && currentPath.startsWith(p) && p.length > bestLen) {
          best = a;
          bestLen = p.length;
        }
      } catch {
        // ignore
      }
    });

    links.forEach((a) => a.classList.remove("active"));
    if (best) {
      best.classList.add("active");
      const dropdownParent = best.closest(".dropdown-parent");
      if (dropdownParent) dropdownParent.classList.add("active");
    }
  }

  // Sidebar collapse
  function initSidebarCollapse() {
    const btn = qs("#sidebarCollapseBtn");
    if (!btn) return;
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      document.body.classList.toggle("sidebar-collapsed");
      try {
        localStorage.setItem(
          "somamage-sidebar-collapsed",
          document.body.classList.contains("sidebar-collapsed") ? "1" : "0"
        );
      } catch {}
    });

    try {
      if (localStorage.getItem("somamage-sidebar-collapsed") === "1") {
        document.body.classList.add("sidebar-collapsed");
      }
    } catch {}
  }

  // Mobile/off-canvas sidebar
  function initMobileSidebar() {
    const toggleBtn = qs(".menu-toggle");
    const sidebar = qs(".sidebar");
    if (!toggleBtn || !sidebar) return;

    const BREAKPOINT = 992;
    let overlay = qs("#sidebarOverlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "sidebarOverlay";
      overlay.className = "sidebar-overlay";
      document.body.appendChild(overlay);
    }

    function isMobile() {
      return window.innerWidth <= BREAKPOINT;
    }

    function openSidebar() {
      document.body.classList.add("sidebar-open");
      // On mobile we always want the full sidebar (not icon-only collapsed)
      document.body.classList.add("sidebar-mobile");
    }

    function closeSidebar() {
      document.body.classList.remove("sidebar-open");
      document.body.classList.remove("sidebar-mobile");
    }

    toggleBtn.addEventListener("click", function (e) {
      e.preventDefault();
      if (!isMobile()) return;
      if (document.body.classList.contains("sidebar-open")) closeSidebar();
      else openSidebar();
    });

    overlay.addEventListener("click", function () {
      closeSidebar();
    });

    document.addEventListener("keydown", function (e) {
      if ((e.key || "").toLowerCase() === "escape") closeSidebar();
    });

    // Close when navigating on mobile
    qsa(".sidebar-menu a[href]").forEach((a) => {
      a.addEventListener("click", function () {
        if (isMobile()) closeSidebar();
      });
    });

    // Keep layout sane on resize
    window.addEventListener("resize", function () {
      if (!isMobile()) closeSidebar();
    });
  }

  // Tooltip titles for icon-only collapsed sidebar
  function initSidebarTitles() {
    const nav = qs(".sidebar-menu");
    if (!nav) return;
    qsa("a", nav).forEach((a) => {
      const txt = (a.textContent || "").replace(/\s+/g, " ").trim();
      if (txt && !a.getAttribute("title")) a.setAttribute("title", txt);
    });
  }

  // Top search focus shortcut (Ctrl/Cmd+K)
  function initSearchShortcut() {
    const input = qs("#topSearchInput");
    if (!input) return;
    document.addEventListener("keydown", function (e) {
      const isK = (e.key || "").toLowerCase() === "k";
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && isK) {
        e.preventDefault();
        input.focus();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setActiveSidebarLink();
    initSidebarCollapse();
    initMobileSidebar();
    initSidebarTitles();
    initSearchShortcut();
  });
})();


