const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const {LESSONS,QUIZ}=require('./data.js');
const dom=new JSDOM(fs.readFileSync(__dirname+'/index.html','utf8'),{runScripts:'outside-only',url:'https://example.test/aws-cloud-classroom/'});
const w=dom.window,d=w.document;const $=id=>d.getElementById(id);
w.eval(fs.readFileSync(__dirname+'/data.js','utf8')+'\n'+fs.readFileSync(__dirname+'/app.js','utf8'));
assert.equal(d.querySelectorAll('.lesson').length,12);
assert.equal(new Set(LESSONS.map(x=>x.id)).size,12);
assert(LESSONS.every(x=>new URL(x.url).hostname.endsWith('aws.amazon.com')));
assert(QUIZ.every(x=>x.correct>=0&&x.correct<x.a.length));
d.querySelector('.complete').click();assert.equal($('progress').value,1);d.querySelector('.complete').click();assert.equal($('progress').value,0);
$('search').value='DynamoDB';$('search').dispatchEvent(new w.Event('input'));assert.equal(d.querySelectorAll('.lesson').length,1);
$('search').value='NO_MATCH_123';$('search').dispatchEvent(new w.Event('input'));assert.equal($('empty').hidden,false);
$('search').value='';$('search').dispatchEvent(new w.Event('input'));
[...$('filters').children].find(b=>b.textContent==='Compute').click();assert.equal(d.querySelectorAll('.lesson').length,2);$('filters').firstChild.click();
$('step').click();assert($('step-detail').textContent.includes('domain'));for(let i=0;i<4;i++)$('step').click();assert.equal(d.querySelector('.flow .active').textContent,'1. Browser');
$('scenario').value='api';$('scenario').dispatchEvent(new w.Event('change'));assert.equal(d.querySelectorAll('.flow .active').length,0);$('flow').lastChild.click();assert($('step-detail').textContent.includes('Order key'));$('restart').click();assert.equal(d.querySelectorAll('.flow .active').length,0);
QUIZ.forEach(q=>{$('answers').children[q.correct].click();$('answers').children[q.correct].click();$('next').click();});assert.equal($('question').textContent,'6 / 6 correct answers');$('retry').click();assert.equal($('answers').children.length,3);$('answers').children[1].click();assert($('feedback').textContent.includes('Correct answer'));
d.querySelector('.complete').click();w.confirm=()=>false;$('clear-progress').click();assert.equal($('progress').value,1);w.confirm=()=>true;$('clear-progress').click();assert.equal($('progress').value,0);
console.log('PASS: lesson data, source domains, filters, search/empty, progress toggle, flow navigation/restart/scenario reset, perfect quiz, duplicate answer guard, retry/wrong answer, reset cancel/confirm.');
// English-only contract and translation invariants.
for(const file of ['index.html','app.js','data.js']) assert(!/[\u0B80-\u0BFF]/u.test(fs.readFileSync(__dirname+'/'+file,'utf8')),file+' must contain no Tamil text');
assert.equal(d.documentElement.lang,'en');
assert.equal(LESSONS.length,12);assert.equal(QUIZ.length,6);
assert.deepEqual([...new Set(LESSONS.map(l=>l.category))],['Basics','Security','Compute','Storage','Data','Network']);
assert.equal($('clear-progress').textContent,'Clear learning progress');
assert.equal($('question-count').textContent,'Question 1 / 6');
assert.equal($('restart').textContent,'Restart');
// Saved progress remains compatible with the existing application.
function boot(saved,blocked=false){const dom=new JSDOM(fs.readFileSync(__dirname+'/index.html','utf8'),{runScripts:'outside-only',url:'https://example.test/aws-cloud-classroom/'});const win=dom.window;if(saved!==undefined)win.localStorage.setItem('aws-classroom-v1',saved);if(blocked)Object.defineProperty(win,'localStorage',{get(){throw new Error('Storage blocked');}});win.eval(fs.readFileSync(__dirname+'/data.js','utf8')+'\n'+fs.readFileSync(__dirname+'/app.js','utf8'));return win;}
const saved=boot('["cloud","iam","unknown"]');assert.equal(saved.document.getElementById('progress').value,2);assert.equal(saved.document.querySelector('.complete').textContent,'✓ Completed');saved.document.querySelector('.complete').click();assert.deepEqual(JSON.parse(saved.localStorage.getItem('aws-classroom-v1')),['iam']);
const invalid=boot('invalid');assert.equal(invalid.document.getElementById('progress').value,0);
const blocked=boot(undefined,true);blocked.document.querySelector('.complete').click();assert.equal(blocked.document.getElementById('progress').value,1);assert.equal(blocked.document.getElementById('storage-status').textContent,'Browser storage is unavailable. Progress will last only for this session.');
for(const scenario of ['static','api']){$('scenario').value=scenario;$('scenario').dispatchEvent(new w.Event('change'));for(let i=0;i<4;i++){$('step').click();assert($('step-detail').textContent.length>20);assert(!/[\u0B80-\u0BFF]/u.test($('step-detail').textContent));}assert.equal($('step').textContent,'Back to first step ↺');$('step').click();assert.equal($('step').textContent,'Next step →');}
console.log('PASS: English-only runtime, HTML language, labels, lesson counts/categories, saved-progress compatibility, malformed/blocked storage, both complete architecture scenarios.');
