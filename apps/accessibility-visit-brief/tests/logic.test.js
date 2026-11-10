import {test} from 'node:test';import assert from 'node:assert/strict';import {makeBrief,normalize,fields} from '../logic.js';
test('normalizes untrusted storage',()=>{assert.equal(normalize({venue:42}).venue,'');assert.equal(Object.keys(normalize(null)).length,fields.length);});
test('marks unknown facts',()=>assert.match(makeBrief({}),/Destination: Not recorded/));
test('includes user content and disclaimer',()=>{const brief=makeBrief({venue:'Museum'});assert.match(brief,/Destination: Museum/);assert.match(brief,/not an accessibility certification/);});
