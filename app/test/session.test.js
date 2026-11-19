// Tests the safety gate, tools and report flow with a fake (offline) Gemini client.
import { test } from 'node:test';
import assert from 'node:assert/strict';
process.env.STORE = 'file';
process.env.DATA_FILE = '/tmp/fixsaathi-test/jobs.json';
const { RepairSession } = await import('../src/session.js');
const { store } = await import('../src/store.js');

const offlineAI = { models: { generateContent: async () => { throw new Error('offline'); } } };

function newSession() {
  const events = [];
  const s = new RepairSession({ ai: offlineAI, technician: 'Ravi', complaint: 'Fan slow', emit: (e) => events.push(e) });
  return { s, events };
}

test('repair steps are blocked until safety is confirmed', async () => {
  const { s, events } = newSession();
  const r = await s.handleTool('give_step', { step_number: 1, instruction: 'Open the canopy', needs_power_off: true });
  assert.equal(r.blocked, true);
  assert.equal(s.job.steps.length, 0);
  assert.equal(s.job.safety.blockedAttempts, 1);
  assert.ok(events.some((e) => e.type === 'blocked'));
});

test('safety needs both power-off and tester confirmation', async () => {
  const { s } = newSession();
  const r = await s.handleTool('confirm_safety', { power_off_confirmed: true, tester_checked: false, checks: [] });
  assert.equal(r.confirmed, false);
  assert.equal(s.job.safety.confirmed, false);
});

test('after safety, steps are shown; non-risky steps never blocked', async () => {
  const { s, events } = newSession();
  const a = await s.handleTool('give_step', { step_number: 1, instruction: 'Show me the label', needs_power_off: false });
  assert.equal(a.shown, true);
  await s.handleTool('confirm_safety', { power_off_confirmed: true, tester_checked: true, checks: ['MCB off', 'Tester shows no live line'] });
  const b = await s.handleTool('give_step', { step_number: 2, instruction: 'Open the canopy', needs_power_off: true });
  assert.equal(b.shown, true);
  assert.equal(s.job.steps.length, 2);
  assert.ok(events.some((e) => e.type === 'safety' && e.confirmed));
});

test('diagnosis falls back to the knowledge base when the model is unavailable', async () => {
  const { s } = newSession();
  const d = await s.handleTool('get_diagnosis', { appliance: 'ceiling fan', symptom: 'fan runs slow' });
  assert.equal(d.source, 'knowledge_base');
  assert.match(d.causes[0].cause, /capacitor/i);
});

test('complete_job writes a report and saves the job', async () => {
  const { s, events } = newSession();
  s.addFrame('AAAA');
  await s.handleTool('confirm_safety', { power_off_confirmed: true, tester_checked: true, checks: ['MCB off'] });
  await s.handleTool('give_step', { step_number: 1, instruction: 'Replace capacitor', needs_power_off: true });
  const r = await s.handleTool('complete_job', { outcome: 'fixed', fault_found: 'Weak capacitor', parts_replaced: ['2.5 uF capacitor'] });
  assert.equal(r.done, true);
  assert.equal(s.job.status, 'completed');
  assert.equal(s.job.report.first_time_fix, true);
  const saved = await store.get(s.job.id);
  assert.equal(saved.report.fault_found, 'Weak capacitor');
  assert.ok(events.some((e) => e.type === 'report'));
});

test('escalation marks the job escalated', async () => {
  const { s } = newSession();
  await s.handleTool('escalate_to_senior', { reason: 'Gas leak suspected' });
  assert.equal(s.job.status, 'escalated');
});
