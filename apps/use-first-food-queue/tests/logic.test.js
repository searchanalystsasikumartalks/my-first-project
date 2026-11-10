import {test} from 'node:test';import assert from 'node:assert/strict';import {dayGap,dateLabel,sortFoods,validFoods} from '../logic.js';
test('date arithmetic across year and leap day',()=>{assert.equal(dayGap('2027-01-01','2026-12-31'),1);assert.equal(dayGap('2028-03-01','2028-02-28'),2);assert.equal(dayGap('', '2026-01-01'),null);});
test('never claims safety',()=>{assert.equal(dateLabel('2026-01-01','2026-01-02'),'1 day past entered date');assert.equal(dateLabel('','2026-01-02'),'No date recorded');});
test('undated food sorts last without mutation',()=>{const a=[{name:'B',date:''},{name:'A',date:'2026-01-01'}];assert.equal(sortFoods(a)[0].name,'A');assert.equal(a[0].name,'B');});
test('rejects invalid saved data',()=>assert.equal(validFoods([{}]),false));
