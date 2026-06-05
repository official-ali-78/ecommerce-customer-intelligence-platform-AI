/**
 * Plotly charts: render, theme sync, download toolbars.
 */
(function () {
  var THEME_COLORS = {
    light: {
      font: "#334155",
      title: "#0f172a",
      grid: "#e2e8f0",
      line: "#cbd5e1",
    },
    dark: {
      font: "#cbd5e1",
      title: "#f1f5f9",
      grid: "#334155",
      line: "#475569",
    },
  };

  function themeColors() {
    var theme =
      (window.AnalyticsUI && window.AnalyticsUI.getTheme()) ||
      document.documentElement.getAttribute("data-theme") ||
      "light";
    return THEME_COLORS[theme === "dark" ? "dark" : "light"];
  }

  function addChartToolbar(el, chartId, title) {
    var panel = el.closest(".chart-panel");
    if (!panel) {
      panel = document.createElement("div");
      panel.className = "chart-panel glass-card";
      el.parentNode.insertBefore(panel, el);
      panel.appendChild(el);
    }
    if (panel.querySelector(".chart-toolbar")) return;
    var toolbar = document.createElement("div");
    toolbar.className = "chart-toolbar";
    toolbar.innerHTML =
      '<span class="chart-toolbar-title">' +
      (title || chartId) +
      '</span><button type="button" class="btn-chart-download" data-chart-download="' +
      chartId +
      '" title="Download chart" aria-label="Download chart"><i class="bi bi-download"></i></button>';
    panel.insertBefore(toolbar, el);
  }

  function applyThemeToChart(el) {
    if (!el || !el.layout) return;
    var c = themeColors();
    var axisUpdate = {
      gridcolor: c.grid,
      linecolor: c.line,
      zerolinecolor: c.grid,
      color: c.font,
    };
    Plotly.relayout(el, {
      "font.color": c.font,
      "title.font.color": c.title,
      "xaxis.gridcolor": c.grid,
      "xaxis.linecolor": c.line,
      "xaxis.zerolinecolor": c.grid,
      "xaxis.color": c.font,
      "yaxis.gridcolor": c.grid,
      "yaxis.linecolor": c.line,
      "yaxis.zerolinecolor": c.grid,
      "yaxis.color": c.font,
    });
    if (el.layout.xaxis2) {
      Plotly.relayout(el, {
        "xaxis2.gridcolor": c.grid,
        "yaxis2.gridcolor": c.grid,
      });
    }
  }

  function renderCharts(charts) {
    if (!charts || typeof Plotly === "undefined") return;
    Object.keys(charts).forEach(function (id) {
      var el = document.getElementById("chart-" + id);
      if (!el) return;
      try {
        var fig = charts[id];
        if (typeof fig === "string") fig = JSON.parse(fig);
        var title =
          fig.layout && fig.layout.title && fig.layout.title.text
            ? fig.layout.title.text
            : id.replace(/_/g, " ");
        addChartToolbar(el, id, title);
        Plotly.newPlot(el, fig.data, fig.layout, {
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
          modeBarButtonsToRemove: ["lasso2d", "select2d"],
        }).then(function () {
          applyThemeToChart(el);
        });
      } catch (e) {
        console.error("Plotly render failed:", id, e);
        el.innerHTML =
          '<p class="text-muted small p-3">Chart unavailable.</p>';
      }
    });
  }

  function applyTheme(theme) {
    document.querySelectorAll(".plotly-chart").forEach(function (el) {
      if (el.data) applyThemeToChart(el);
    });
  }

  window.AnalyticsCharts = {
    render: renderCharts,
    applyTheme: applyTheme,
  };

  document.addEventListener("DOMContentLoaded", function () {
    if (window.PLOTLY_CHARTS) {
      renderCharts(window.PLOTLY_CHARTS);
    }
  });

  var resizeTimer;
  window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      document.querySelectorAll(".plotly-chart").forEach(function (el) {
        if (el.data) Plotly.Plots.resize(el);
      });
    }, 150);
  });
})();
