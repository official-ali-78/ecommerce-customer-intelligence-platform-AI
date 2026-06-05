/**
 * Theme toggle, chart download, scroll animations.
 */
(function () {
  var STORAGE_KEY = "analytics-theme";

  function getPreferredTheme() {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "light" || saved === "dark") return saved;
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);
    document.querySelectorAll("[data-theme-icon]").forEach(function (el) {
      el.className =
        theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
    });
    if (window.AnalyticsCharts && window.AnalyticsCharts.applyTheme) {
      window.AnalyticsCharts.applyTheme(theme);
    }
  }

  function initThemeToggle() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var current =
          document.documentElement.getAttribute("data-theme") || "light";
        applyTheme(current === "dark" ? "light" : "dark");
      });
    });
  }

  function initScrollAnimations() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
    );
    document
      .querySelectorAll(".chart-panel:not(.animate-in)")
      .forEach(function (el, i) {
        el.classList.add("animate-in");
        el.style.setProperty("--delay", 0.1 + i * 0.06 + "s");
        observer.observe(el);
      });
  }

  function slugify(text) {
    return (text || "chart")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  }

  function downloadChart(chartId) {
    var el = document.getElementById("chart-" + chartId);
    if (!el || !el.data) return;
    var title =
      el._fullLayout && el._fullLayout.title && el._fullLayout.title.text
        ? el._fullLayout.title.text
        : chartId;
    var filename = slugify(title) + ".png";
    Plotly.downloadImage(el, {
      format: "png",
      width: 1200,
      height: 700,
      filename: filename.replace(/\.png$/, ""),
    });
  }

  function initChartDownloads() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-chart-download]");
      if (!btn) return;
      e.preventDefault();
      var chartId = btn.getAttribute("data-chart-download");
      if (chartId) downloadChart(chartId);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    applyTheme(
      document.documentElement.getAttribute("data-theme") || getPreferredTheme()
    );
    initThemeToggle();
    initChartDownloads();
    setTimeout(initScrollAnimations, 100);
  });

  window.AnalyticsUI = {
    applyTheme: applyTheme,
    getTheme: function () {
      return document.documentElement.getAttribute("data-theme") || "light";
    },
    downloadChart: downloadChart,
  };
})();
