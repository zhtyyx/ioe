// Shared page chrome and tabular layout. Business content and form behavior stay in templates.
(() => {
  const main = document.querySelector('.main-content');
  if (!main || !document.body.classList.contains('app-layout')) return;
  const title = main.querySelector('.page-title');
  if (title) {
    const description = title.nextElementSibling;
    if (description?.tagName === 'P') description.classList.add('page-description', 'visually-hidden');
    let wrapper = title.parentElement;
    const invisible = '.page-title, .page-description, .page-intro-empty';
    while (wrapper && wrapper !== main) {
      const visibleChildren = [...wrapper.children].filter(el => !el.matches(invisible));
      const ownText = [...wrapper.childNodes].some(node => node.nodeType === 3 && node.textContent.trim());
      if (!visibleChildren.length && !ownText) {
        wrapper.classList.add('page-intro-empty');
        wrapper = wrapper.parentElement;
      } else {
        if (!wrapper.querySelector('table, form, .card-body, section') && wrapper.querySelector('a, button, .date-label')) wrapper.classList.add('page-action-bar');
        break;
      }
    }
  }
  // These are repeated navigation captions; the persistent top bar identifies the page.
  main.querySelectorAll('.breadcrumb, nav[aria-label=breadcrumb]').forEach(el => el.classList.add('page-intro-empty'));
  main.querySelector('.cashier-header')?.classList.add('visually-hidden');

  function tableLayout(table) {
    if (!table.tHead) return;
    table.classList.add('table', 'data-table');
    table.closest('.card')?.classList.add('list-panel');
    const headers = [...table.tHead.rows[table.tHead.rows.length - 1].cells];
    const columns = headers.map(header => {
      const text = header.textContent.trim();
      if (/^(操作|操作选项|Actions?|Operations?)$/i.test(text)) return 'data-actions';
      if (/数量|金额|单价|售价|成本|利润|折扣|积分|余额|库存$|消费|销售额|订单数|销量|次数|充值额|^(Quantity|Qty|Price|Unit price|Amount|Total|Subtotal|Cost|Profit|Discount|Points|Balance|Stock|Current stock|Warning stock|Stock level|Count|Orders|Sales|Revenue)/i.test(text) && !/时间|日期|类型|记录|Date|Time|Type/i.test(text)) return 'data-number';
      if (/时间|日期|Date|Created|Updated/i.test(text)) return 'data-date';
      return '';
    });
    for (const row of table.rows) {
      if (row.cells.length !== headers.length || [...row.cells].some(cell => cell.colSpan > 1)) continue;
      [...row.cells].forEach((cell, index) => { if (columns[index]) cell.classList.add(columns[index]); });
    }
  }
  main.querySelectorAll('table').forEach(tableLayout);
  new MutationObserver(records => {
    const tables = new Set();
    for (const record of records) {
      if (record.target.closest?.('table')) tables.add(record.target.closest('table'));
      for (const node of record.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (node.matches('table')) tables.add(node);
        node.querySelectorAll('table').forEach(table => tables.add(table));
      }
    }
    tables.forEach(tableLayout);
  }).observe(main, {childList: true, subtree: true});
})();
