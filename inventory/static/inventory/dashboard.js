(() => {
  const canvas = document.getElementById('salesChart');
  if (!canvas || typeof Chart === 'undefined') return;
  const series = JSON.parse(document.getElementById('sales-trend-data').textContent);
  const english = document.documentElement.lang === 'en';
  const tokens = () => {
    const css = getComputedStyle(document.documentElement);
    return { muted: css.getPropertyValue('--muted').trim(), border: css.getPropertyValue('--separator').trim(), accent: css.getPropertyValue('--accent').trim() };
  };
  const colors = tokens();
  const chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: series.map(day => day.date.replace('-', '/')),
      datasets: [{
        label: english ? 'Sales amount' : '销售额', data: series.map(day => day.amount),
        borderColor: colors.accent, borderWidth: 2.5, fill: true, tension: .35,
        pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: colors.accent,
        pointBorderWidth: 2, pointBorderColor: getComputedStyle(document.body).getPropertyValue('--surface').trim(),
        backgroundColor: context => {
          const {ctx, chartArea} = context.chart;
          if (!chartArea) return 'rgba(37,99,235,.08)';
          const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
          gradient.addColorStop(0, 'rgba(37,99,235,.16)'); gradient.addColorStop(1, 'rgba(37,99,235,0)');
          return gradient;
        },
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? false : {duration: 500},
      interaction: {mode: 'index', intersect: false},
      plugins: {legend: {display: false}, tooltip: {displayColors: false, padding: 12, cornerRadius: 8, callbacks: {label: context => `¥ ${context.parsed.y.toFixed(2)}`}}},
      scales: {
        x: {border: {display: false}, grid: {display: false}, ticks: {color: colors.muted, font: {size: 10}, maxRotation: 0}},
        y: {beginAtZero: true, border: {display: false}, grid: {color: colors.border}, ticks: {maxTicksLimit: 5, color: colors.muted, font: {size: 10}, padding: 12, callback: value => `¥${value}`}},
      },
    },
  });
  document.addEventListener('ioe:theme-change', () => {
    const next = tokens();
    chart.options.scales.x.ticks.color = next.muted;
    chart.options.scales.y.ticks.color = next.muted;
    chart.options.scales.y.grid.color = next.border;
    chart.data.datasets[0].borderColor = next.accent;
    chart.data.datasets[0].pointBackgroundColor = next.accent;
    chart.update('none');
  });
})();
