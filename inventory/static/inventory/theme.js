// Set the theme before first paint; storage may be disabled in private browsers.
(() => {
  let theme = 'light';
  try { theme = localStorage.getItem('ioe-theme') || theme; } catch (_) {}
  document.documentElement.dataset.theme = theme === 'dark' ? 'dark' : 'light';
})();
