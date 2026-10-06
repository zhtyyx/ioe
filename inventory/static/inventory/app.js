(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector('.theme-toggle');
  const syncTheme = () => {
    const dark = root.dataset.theme === 'dark';
    themeButton?.setAttribute('aria-pressed', String(dark));
    if (themeButton) themeButton.querySelector('i').className = `bi bi-${dark ? 'sun' : 'moon'}`;
  };
  syncTheme();
  themeButton?.addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('ioe-theme', root.dataset.theme); } catch (_) {}
    syncTheme();
    document.dispatchEvent(new Event('ioe:theme-change'));
  });
  const pageLabel = document.querySelector('#current-page-label');
  if (pageLabel) pageLabel.textContent = document.title.split(' - ')[0];
  document.querySelector('.sidebar-link.active')?.setAttribute('aria-current', 'page');
  const sidebar = document.querySelector('.app-sidebar');
  const toggle = document.querySelector('.mobile-menu-toggle');
  const backdrop = document.querySelector('.sidebar-backdrop');
  const workspace = document.querySelector('.app-workspace');
  const mobile = window.matchMedia('(max-width: 991px)');
  let returnFocus;
  function setMenu(open) {
    document.body.classList.toggle('menu-open', open);
    toggle?.setAttribute('aria-expanded', String(open));
    if (backdrop) backdrop.hidden = !open;
    if (sidebar) sidebar.inert = mobile.matches && !open;
    if (workspace) workspace.inert = mobile.matches && open;
    if (open) {
      returnFocus = document.activeElement;
      sidebar?.querySelector('a')?.focus();
    } else if (returnFocus) {
      returnFocus.focus();
      returnFocus = null;
    }
  }
  setMenu(false);
  toggle?.addEventListener('click', () => setMenu(!document.body.classList.contains('menu-open')));
  backdrop?.addEventListener('click', () => setMenu(false));
  sidebar?.addEventListener('click', event => { if (event.target.closest('a') && mobile.matches) setMenu(false); });
  mobile.addEventListener('change', () => setMenu(false));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') setMenu(false);
    if (event.key === 'Tab' && document.body.classList.contains('menu-open')) {
      const links = [...sidebar.querySelectorAll('a, button')];
      const first = links[0], last = links[links.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
    if (event.key === '/' && !event.metaKey && !event.ctrlKey && !event.altKey && !event.target.closest('input, textarea, select, [contenteditable="true"]')) {
      const search = document.querySelector('.global-search input');
      if (search && search.getClientRects().length) { event.preventDefault(); search.focus(); }
    }
  });
  // Preserve server-rendered Django forms and Bootstrap interaction behavior.
  document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]):not([type="submit"]), textarea, select').forEach(field => {
    if (!field.closest('.app-topbar') && !field.classList.contains('form-control') && !field.classList.contains('form-select')) {
      field.classList.add(field.tagName === 'SELECT' ? 'form-select' : 'form-control');
    }
  });
  document.querySelectorAll('form').forEach(form => form.addEventListener('submit', event => {
    if (form.noValidate) return;
    if (!form.checkValidity()) { event.preventDefault(); form.reportValidity(); }
    form.classList.add('was-validated');
  }));
  // Errors and stock warnings remain visible until explicitly dismissed.
})();
