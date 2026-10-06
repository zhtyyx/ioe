// Match canvas labels and tooltips to the same theme as the surrounding UI.
(() => {
  const registered = new WeakSet();
  function colors() {
    const css = getComputedStyle(document.documentElement);
    return Object.fromEntries(['muted', 'foreground', 'separator', 'overlay'].map(name => [name, css.getPropertyValue(`--${name}`).trim()]));
  }
  function styleChart(chart) {
    const theme = colors();
    chart.options.color = theme.muted;
    for (const scale of Object.values(chart.options.scales || {})) {
      if (scale.ticks) scale.ticks.color = theme.muted;
      if (scale.grid) scale.grid.color = theme.separator;
      if (scale.border) scale.border.color = theme.separator;
      if (scale.angleLines) scale.angleLines.color = theme.separator;
    }
    const plugins = chart.options.plugins;
    if (plugins?.legend?.labels) plugins.legend.labels.color = theme.muted;
    if (plugins?.title) plugins.title.color = theme.foreground;
    if (plugins?.tooltip) Object.assign(plugins.tooltip, {
      backgroundColor: theme.overlay, titleColor: theme.foreground,
      bodyColor: theme.foreground, borderColor: theme.separator, borderWidth: 1,
    });
  }
  function syncCharts() {
    const Chart = window.Chart;
    if (!Chart) return;
    if (!registered.has(Chart)) {
      Chart.register({id: 'ioeTheme', beforeUpdate: styleChart});
      registered.add(Chart);
    }
    Chart.defaults.color = colors().muted;
    Chart.defaults.borderColor = colors().separator;
    Object.values(Chart.instances).forEach(chart => chart.update('none'));
  }
  syncCharts();
  document.addEventListener('DOMContentLoaded', syncCharts);
  document.addEventListener('ioe:theme-change', syncCharts);
})();
