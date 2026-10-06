// Run with ego-browser nodejs in an existing task space against the demo database.
// Set globalThis.IOE_UI_SPACE and globalThis.IOE_UI_URL before this script.
// Use a disposable preview. No data is saved.
const p=(await taskSpace(Number(globalThis.IOE_UI_SPACE))).page('p1');
const base=globalThis.IOE_UI_URL || 'http://127.0.0.1:8783';
await p.goto(base+'/products/create/');
await p.evaluate(()=>{
 const form=document.createElement('form');form.id='ui-fixture';form.innerHTML='<label for="ui-select">Fixture</label><select id="ui-select" name="choice" required><option value="">Pick</option><option value="a">Alpha</option><option disabled value="b">Beta</option><option value="c">Charlie</option></select><input type="search" name="q"><button type="reset">Reset</button>';
 document.querySelector('main').prepend(form);window.uiEvents=[];form.addEventListener('change',e=>uiEvents.push(e.target.value));form.addEventListener('submit',e=>e.preventDefault());
});
await p.waitForSelector('#ui-fixture .select__trigger');
await p.click('#ui-fixture .select__trigger');await p.press('#ui-fixture .select__trigger','ArrowDown');await p.press('#ui-fixture .select__trigger','ArrowDown');await p.press('#ui-fixture .select__trigger','Enter');
const keyboard = await p.evaluate(()=>({keyboard:document.querySelector('#ui-select').value,formData:new FormData(document.querySelector('#ui-fixture')).get('choice'),events:uiEvents}));
if (keyboard.keyboard !== 'c' || keyboard.formData !== 'c' || keyboard.events.length !== 1) throw new Error(JSON.stringify(keyboard));
await p.click('#ui-fixture button[type=reset]');await p.waitForFunction(()=>document.querySelector('#ui-fixture .select__value').textContent==='Pick');
const invalid = await p.evaluate(()=>{const s=document.querySelector('#ui-select');s.reportValidity();return {reset:s.value,validation:!document.querySelector('#ui-fixture .ioe-select-error').hidden,focus:document.activeElement.className};});
if (invalid.reset || !invalid.validation || invalid.focus !== 'select__trigger') throw new Error(JSON.stringify(invalid));
await p.evaluate(()=>{const s=document.querySelector('#ui-select');s.add(new Option('Delta','d'));s.value='d';});
await p.waitForFunction(()=>document.querySelector('#ui-fixture .select__value').textContent==='Delta');
await p.click('#ui-fixture .select__trigger');await p.press('#ui-fixture .select__trigger','Escape');
if (!await p.evaluate(()=>document.querySelector('#ui-fixture .select__trigger').getAttribute('aria-expanded') === 'false')) throw new Error('Escape did not close select');
await p.fill('#ui-fixture input','hello');await p.click('#ui-fixture .search-field__clear-button');if (!await p.evaluate(()=>document.querySelector('#ui-fixture input').value === '' && document.activeElement.tagName === 'INPUT')) throw new Error('Search clear/focus failed');
await p.evaluate(()=>{const s=document.querySelector('#ui-select');jQuery(s).val('a').trigger('change');});
await p.waitForFunction(()=>document.querySelector('#ui-fixture .select__value').textContent==='Alpha');
await p.evaluate(()=>document.querySelector('#ui-select').disabled=true);
await p.waitForFunction(()=>document.querySelector('#ui-fixture .select__trigger').disabled);
await p.evaluate(()=>document.querySelector('#ui-fixture').remove());

console.log('HeroUI interaction smoke completed');
