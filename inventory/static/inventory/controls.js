// HeroUI CSS components for Django forms. Native fields remain the submission source.
(() => {
  let nextId = 0;
  let opened = null;
  const states = new WeakMap();
  const english = document.documentElement.lang === 'en';
  const make = (tag, className) => Object.assign(document.createElement(tag), {className});
  function enhanceSelect(source) {
    if (states.has(source)) return;
    const root = make('div', 'select ioe-select');
    const trigger = make('button', 'select__trigger');
    const value = make('span', 'select__value');
    const indicator = make('i', 'select__indicator bi bi-chevron-down');
    const popup = make('div', 'select__popover ioe-select-popover');
    const list = make('div', 'list-box');
    const error = make('span', 'field-error ioe-select-error');
    error.hidden = true;
    const id = `ioe-select-${++nextId}`;
    trigger.type = 'button';
    trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-controls', id);
    error.id = `${id}-error`;
    error.setAttribute('aria-live', 'polite');
    trigger.setAttribute('aria-expanded', 'false');
    indicator.setAttribute('aria-hidden', 'true');
    list.id = id;
    list.setAttribute('role', 'listbox');
    popup.setAttribute('popover', 'auto');
    popup.append(list);
    trigger.append(value, indicator);
    for (const name of source.classList) if (/^(m[setbxy]?|col)-/.test(name)) root.classList.add(name);
    source.before(root);
    root.append(source, trigger, popup, error);
    source.classList.add('ioe-select-source');
    source.tabIndex = -1;
    source.setAttribute('aria-hidden', 'true');
    let active = -1, buffer = '', lastKey = 0;
    const options = () => [...source.options];
    const disabled = option => option.disabled || option.parentElement.disabled;
    const isOpen = () => trigger.getAttribute('aria-expanded') === 'true';
    function position() {
      const rect = trigger.getBoundingClientRect();
      const available = Math.max(100, Math.max(innerHeight - rect.bottom, rect.top) - 12);
      popup.style.width = `${Math.min(Math.max(rect.width, 160), innerWidth - 16)}px`;
      popup.style.maxHeight = `${Math.min(280, available)}px`;
      popup.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - parseFloat(popup.style.width) - 8))}px`;
      popup.style.top = `${rect.bottom + 4}px`;
      if (rect.bottom + 4 + popup.offsetHeight > innerHeight - 8) popup.style.top = `${Math.max(8, rect.top - popup.offsetHeight - 4)}px`;
    }
    function close() {
      if (popup.matches(':popover-open')) popup.hidePopover();
      trigger.setAttribute('aria-expanded', 'false');
      trigger.removeAttribute('aria-activedescendant');
      if (opened === state) opened = null;
    }
    function highlight(index) {
      active = index;
      [...list.children].forEach((item, i) => item.dataset.focused = String(i === active));
      if (index >= 0) {
        trigger.setAttribute('aria-activedescendant', `${id}-${index}`);
        list.children[index]?.scrollIntoView({block: 'nearest'});
      }
    }
    function sync() {
      value.textContent = [...source.selectedOptions].map(o => o.textContent.trim()).join(', ') || (english ? 'Select' : '请选择');
      trigger.disabled = source.matches(':disabled');
      trigger.setAttribute('aria-required', String(source.required));
      trigger.setAttribute('aria-label', source.getAttribute('aria-label') || [...source.labels || []].map(l => l.textContent.trim()).join(' ') || source.name || value.textContent);
      trigger.setAttribute('aria-invalid', String(source.classList.contains('is-invalid') || source.getAttribute('aria-invalid') === 'true'));
      const description = source.getAttribute('aria-describedby');
      trigger.setAttribute('aria-describedby', [description, error.hidden ? '' : error.id].filter(Boolean).join(' '));
      if (source.validity.valid) { error.hidden = true; error.textContent = ''; }
      root.hidden = source.hidden || source.classList.contains('d-none') || source.style.display === 'none';
      root.style.width = source.style.width || '';
      root.style.maxWidth = source.style.maxWidth || '';
      list.setAttribute('aria-multiselectable', String(source.multiple));
      list.replaceChildren(...options().map((option, index) => {
        const item = make('div', 'list-box-item');
        item.id = `${id}-${index}`;
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', String(option.selected));
        item.setAttribute('aria-disabled', String(disabled(option)));
        item.hidden = option.hidden;
        item.textContent = option.parentElement.tagName === 'OPTGROUP' ? `${option.parentElement.label} · ${option.textContent}` : option.textContent;
        item.addEventListener('pointerdown', event => event.preventDefault());
        item.addEventListener('click', () => choose(index));
        return item;
      }));
      if (trigger.disabled) close();
      if (isOpen()) { highlight(active); position(); }
    }
    function open() {
      if (trigger.disabled) return;
      opened?.close();
      sync();
      popup.showPopover();
      trigger.setAttribute('aria-expanded', 'true');
      opened = state;
      position();
      highlight(options().findIndex(o => o.selected && !disabled(o)));
    }
    function choose(index) {
      const option = options()[index];
      if (!option || disabled(option)) return;
      if (source.multiple) option.selected = !option.selected;
      else source.selectedIndex = index;
      sync();
      if (!source.multiple) close();
      source.dispatchEvent(new Event('input', {bubbles: true}));
      source.dispatchEvent(new Event('change', {bubbles: true}));
    }
    const state = {close, sync};
    states.set(source, state);
    trigger.addEventListener('click', () => isOpen() ? close() : open());
    popup.addEventListener('toggle', event => { if (event.newState === 'closed') close(); });
    trigger.addEventListener('keydown', event => {
      if (event.key === 'Tab' || event.key === 'Escape') { close(); return; }
      if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
        event.preventDefault();
        if (!isOpen()) open();
        const indices = options().flatMap((o, i) => disabled(o) || o.hidden ? [] : [i]);
        const direction = event.key === 'ArrowUp' ? -1 : 1;
        const next = event.key === 'Home' ? indices[0] : event.key === 'End' ? indices.at(-1) : indices[Math.max(0, Math.min(indices.length - 1, indices.indexOf(active) + direction))];
        highlight(next ?? -1);
      } else if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (isOpen()) choose(active); else open();
      } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault();
        if (!isOpen()) open();
        buffer = Date.now() - lastKey > 700 ? event.key : buffer + event.key;
        lastKey = Date.now();
        highlight(options().findIndex(o => !disabled(o) && o.textContent.trim().toLowerCase().startsWith(buffer.toLowerCase())));
      }
    });
    source.addEventListener('change', sync);
    window.jQuery?.(source).on('change.ioeSelect', sync);
    source.addEventListener('focus', () => trigger.focus());
    source.addEventListener('invalid', event => {
      event.preventDefault();
      error.textContent = source.validationMessage;
      error.hidden = false;
      trigger.setAttribute('aria-describedby', [source.getAttribute('aria-describedby'), error.id].filter(Boolean).join(' '));
      trigger.setAttribute('aria-invalid', 'true');
      const firstInvalid = source.form?.querySelector(':invalid:not(fieldset)');
      if (!firstInvalid || firstInvalid === source) trigger.focus();
    });
    source.form?.addEventListener('reset', () => setTimeout(sync));
    for (const property of ['value', 'selectedIndex']) {
      const descriptor = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, property);
      Object.defineProperty(source, property, {configurable: true, get() { return descriptor.get.call(this); }, set(next) { descriptor.set.call(this, next); sync(); }});
    }
    new MutationObserver(sync).observe(source, {subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['disabled', 'selected', 'label', 'hidden', 'class', 'style', 'required', 'aria-invalid']});
    sync();
  }
  function enhanceSearch(input) {
    if (input.dataset.herouiSearch) return;
    input.dataset.herouiSearch = 'true';
    const root = make('div', 'search-field ioe-search');
    const group = make('div', 'search-field__group');
    const icon = make('i', 'search-field__search-icon bi bi-search');
    const clear = make('button', 'search-field__clear-button button button--tertiary button--icon-only');
    icon.setAttribute('aria-hidden', 'true');
    clear.type = 'button';
    clear.setAttribute('aria-label', english ? 'Clear search' : '清空搜索');
    clear.innerHTML = '<i class="bi bi-x" aria-hidden="true"></i>';
    if (!input.getAttribute('aria-label') && !input.labels?.length) input.setAttribute('aria-label', input.placeholder || (english ? 'Search' : '搜索'));
    const previous = input.previousElementSibling;
    if (previous?.matches('.input-group-text') && previous.querySelector('.bi-search, .bi-upc')) previous.hidden = true;
    for (const name of input.classList) if (/^(m[setbxy]?|col)-/.test(name)) root.classList.add(name);
    input.before(root);
    root.append(group);
    group.append(icon, input, clear);
    input.classList.add('search-field__input');
    const sync = () => { clear.hidden = !input.value || input.disabled || input.readOnly; };
    const descriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
    Object.defineProperty(input, 'value', {configurable: true, get() { return descriptor.get.call(this); }, set(next) { descriptor.set.call(this, next); sync(); }});
    new MutationObserver(sync).observe(input, {attributes: true, attributeFilter: ['disabled', 'readonly']});
    input.addEventListener('input', sync);
    input.addEventListener('change', sync);
    input.form?.addEventListener('reset', () => setTimeout(sync));
    clear.addEventListener('click', () => { input.value = ''; input.dispatchEvent(new Event('input', {bubbles: true})); input.dispatchEvent(new Event('change', {bubbles: true})); input.focus(); });
    sync();
  }
  function enhance(root) {
    if (!root.querySelectorAll) return;
    const fields = root.matches?.('select,input') ? [root] : [];
    fields.push(...root.querySelectorAll('select,input'));
    for (const field of fields) {
      if (field.tagName === 'SELECT') enhanceSelect(field);
      else if (field.matches('input[type=search], input[name=search], input[name=q], input#barcode-input, input#item-product-barcode-input, input[id*=search], form[method=get] input[name=barcode]')) enhanceSearch(field);
    }
  }
  enhance(document);
  new MutationObserver(records => records.forEach(record => record.addedNodes.forEach(enhance))).observe(document.body, {childList: true, subtree: true});
  window.addEventListener('resize', () => opened?.close());
  document.addEventListener('scroll', event => { if (opened && !event.target.closest?.('.ioe-select-popover')) opened.close(); }, true);
})();
