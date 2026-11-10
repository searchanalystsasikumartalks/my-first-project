import {test} from 'node:test';import assert from 'node:assert/strict';import {makeTasks,progress,validPacks} from '../logic.js';
test('trims and omits empty tasks',()=>assert.deepEqual(makeTasks(' a \n\n b').map(t=>t.text),['a','b']));
test('counts progress',()=>assert.deepEqual(progress([{tasks:[{done:true},{done:false}]}]),{total:2,done:1}));
test('rejects invalid restore',()=>{assert.equal(validPacks([{}]),false);assert.equal(validPacks(null),false);assert.equal(validPacks([{id:'1',name:'Plan',tasks:makeTasks('Do')}]),true);});
