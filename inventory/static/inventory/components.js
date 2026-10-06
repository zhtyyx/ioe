// Apply HeroUI's framework-agnostic classes to server-rendered and AJAX content.
(() => {
  const iconNames = {
    'arrow-left': 'arrow-left', 'angle-right': 'chevron-right', 'arrow-right': 'arrow-right',
    'info-circle': 'info-circle', 'info': 'info-circle', 'trash': 'trash', 'trash-alt': 'trash',
    'eye': 'eye', 'edit': 'pencil', 'save': 'save', 'barcode': 'upc', 'user-tag': 'person-badge',
    'search': 'search', 'print': 'printer', 'exclamation-triangle': 'exclamation-triangle',
    'warehouse': 'archive', 'user-shield': 'person-check', 'plus': 'plus-lg',
    'file-invoice-dollar': 'receipt', 'box': 'box-seam', 'boxes': 'boxes', 'wallet': 'wallet2',
    'users': 'people', 'user-cog': 'person-gear', 'user-circle': 'person-circle',
    'th': 'grid', 'stop': 'stop', 'square': 'square', 'redo': 'arrow-clockwise', 'qrcode': 'qr-code',
    'percentage': 'percent', 'lightbulb': 'lightbulb', 'image': 'image', 'history': 'clock-history',
    'gift': 'gift', 'filter': 'funnel', 'file-alt': 'file-text', 'exclamation-circle': 'exclamation-circle',
    'envelope': 'envelope', 'download': 'download', 'check-square': 'check-square', 'camera': 'camera',
    'birthday-cake': 'cake', 'shopping-cart': 'cart', 'check-circle': 'check-circle',
  };
  const variants = ['primary', 'secondary', 'tertiary', 'danger', 'danger-soft'];
  const addClasses = (element, ...names) => names.forEach(name => {
    if (!element.classList.contains(name)) element.classList.add(name);
  });
  const disabledAnchors = new WeakMap();
  const language = () => document.documentElement.lang === 'en' ? 'en' : 'zh';
  const iconLabel = button => {
    const labels = {
      'bi-pencil': ['编辑', 'Edit'], 'bi-trash': ['删除', 'Delete'],
      'bi-eye': ['查看详情', 'View details'], 'bi-search': ['查找', 'Search'],
      'bi-cash-coin': ['充值', 'Recharge'], 'bi-wallet2': ['充值', 'Recharge'],
      'bi-list-ul': ['查看详情', 'View details'], 'bi-upc': ['条码', 'Barcode'],
    };
    const icon = button.querySelector('i');
    const label = Object.entries(labels).find(([name]) => icon?.classList.contains(name))?.[1];
    return label?.[language() === 'en' ? 1 : 0];
  };
  function each(scope, selector, callback) {
    if (scope.nodeType !== 1 && scope.nodeType !== 9) return;
    if (scope.matches?.(selector)) callback(scope);
    scope.querySelectorAll(selector).forEach(callback);
  }
  function enhance(scope) {
    each(scope, 'i.fas, i.far, i.fa', icon => {
      const oldName = [...icon.classList].find(name => name.startsWith('fa-'))?.slice(3);
      const nextName = iconNames[oldName];
      if (nextName) {
        icon.classList.remove('fas', 'far', 'fa', `fa-${oldName}`);
        icon.classList.add('bi', `bi-${nextName}`);
        icon.setAttribute('aria-hidden', 'true');
      }
    });
    each(scope, '.btn, a.page-link, a[role=button], button:not(.sidebar-backdrop):not(.select__trigger):not(.search-field__clear-button), input[type=submit], input[type=button], input[type=reset]', button => {
      if (!button.classList.contains('btn')) {
        addClasses(button, 'button');
        if (![...button.classList].some(c => variants.includes(c.replace('button--', '')))) addClasses(button, button.matches('.swal2-confirm') ? 'button--primary' : 'button--secondary');
        if (button.matches('.btn-close, .swal2-close')) addClasses(button, 'button--icon-only');
        return;
      }
      let variant = 'secondary';
      if (button.classList.contains('btn-primary') || button.classList.contains('btn-success')) variant = 'primary';
      if (button.classList.contains('btn-danger')) variant = 'danger';
      if (button.classList.contains('btn-outline-danger')) variant = 'danger-soft';
      if (button.classList.contains('btn-link')) variant = 'tertiary';
      for (const name of variants) {
        if (name !== variant && button.classList.contains(`button--${name}`)) button.classList.remove(`button--${name}`);
      }
      addClasses(button, 'button', `button--${variant}`);
      const small = button.classList.contains('btn-sm') || Boolean(button.closest('.btn-group-sm'));
      if (small) addClasses(button, 'button--sm');
      else if (button.classList.contains('button--sm')) button.classList.remove('button--sm');
      if (button.classList.contains('btn-lg')) addClasses(button, 'button--lg');
      else if (button.classList.contains('button--lg')) button.classList.remove('button--lg');
      if (!button.textContent.trim() && button.querySelector('i, svg')) {
        addClasses(button, 'button--icon-only');
        const label = button.title || iconLabel(button);
        if (!button.hasAttribute('aria-label') && label) button.setAttribute('aria-label', label);
      } else if (button.classList.contains('button--icon-only')) button.classList.remove('button--icon-only');
      if (button.tagName === 'A') {
        if (button.classList.contains('disabled')) {
          if (!disabledAnchors.has(button)) disabledAnchors.set(button, button.getAttribute('tabindex'));
          button.setAttribute('aria-disabled', 'true');
          button.tabIndex = -1;
        } else if (disabledAnchors.has(button)) {
          const original = disabledAnchors.get(button);
          button.removeAttribute('aria-disabled');
          if (original === null) button.removeAttribute('tabindex');
          else button.setAttribute('tabindex', original);
          disabledAnchors.delete(button);
        }
      }
    });
    each(scope, 'input.form-control:not([type="checkbox"]):not([type="radio"]):not([type="file"]), textarea.form-control', field => addClasses(field, 'input', 'input--full-width'));
    each(scope, '[data-bs-toggle=dropdown]', element => addClasses(element, 'dropdown__trigger'));
    each(scope, '.dropdown-menu', element => addClasses(element, 'dropdown__popover'));
    each(scope, '.dropdown-item', element => addClasses(element, 'list-box-item'));
    each(scope, '.card-header', element => addClasses(element, 'card__header'));
    each(scope, '.card-body', element => addClasses(element, 'card__content'));
    each(scope, '.card-footer', element => addClasses(element, 'card__footer'));
    each(scope, '.badge', element => addClasses(element, 'chip', 'chip--sm', 'chip--soft'));

  }
  enhance(document);
  const pending = new Set();
  let scheduled = false;
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'attributes') pending.add(record.target);
      else for (const node of record.addedNodes) {
        if (node.nodeType === 1) pending.add(node);
        else if (node.parentElement) pending.add(node.parentElement);
      }
    }
    if (scheduled || !pending.size) return;
    scheduled = true;
    queueMicrotask(() => {
      pending.forEach(node => { if (node.isConnected) enhance(node); });
      pending.clear();
      scheduled = false;
    });
  }).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'title', 'disabled']});
})();
