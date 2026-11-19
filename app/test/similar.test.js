import test from 'node:test';
import assert from 'node:assert/strict';
import { similarRepairs, jobDoc, kbDocs } from '../src/similar.js';

test('knowledge base is searchable (keyword fallback, no AI needed)', async () => {
  assert.ok(kbDocs().length > 0);
  const r = await similarRepairs(null, [], 'fan runs slow humming capacitor');
  assert.equal(r.method, 'keyword');
  assert.ok(r.results.length > 0);
  assert.match(r.results[0].title.toLowerCase(), /fan/);
});

test('finished repairs are searchable and ranked first when they match', async () => {
  const job = { id: 'JOB-1', complaint: 'AC not cooling', report: { appliance: 'Split AC', fault_found: 'Low gas leak at flare joint', root_cause: 'refrigerant leak', outcome: 'fixed', work_done: ['Brazed joint', 'Refilled gas'], parts_used: [] } };
  assert.match(jobDoc(job).text, /refrigerant leak/);
  const r = await similarRepairs(null, [job], 'ac not cooling gas leak');
  assert.equal(r.results[0].id, 'JOB-1');
});

test('falls back to keyword search when embeddings fail', async () => {
  const ai = { models: { embedContent: async () => { throw new Error('boom'); } } };
  const r = await similarRepairs(ai, [], 'fan humming slow');
  assert.equal(r.method, 'keyword');
  assert.ok(r.results.length > 0);
});
