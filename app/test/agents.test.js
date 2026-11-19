// Agents with a mocked Gemini response (same shape as the @google/genai SDK).
import { test } from 'node:test';
import assert from 'node:assert/strict';
const { diagnose, locatePart, stepCard } = await import('../src/agents.js');
const { newMetrics } = await import('../src/metrics.js');

const fakeAI = (payload) => ({
  models: {
    generateContent: async (req) => ({
      text: typeof payload === 'string' ? payload : JSON.stringify(payload),
      usageMetadata: { promptTokenCount: 1000, candidatesTokenCount: 200 },
      candidates: [{ content: { parts: [{ text: 'card' }, { inlineData: { data: 'IMG', mimeType: 'image/png' } }] } }],
      _req: req,
    }),
  },
});

test('diagnosis returns model JSON and records usage', async () => {
  const m = newMetrics();
  const d = await diagnose(fakeAI({ causes: [{ cause: 'Weak capacitor', likelihood: 'high', check: 'Swap it' }], next_check: 'Swap it', escalate: false }), { appliance: 'fan', symptom: 'slow' }, null, m);
  assert.equal(d.causes[0].cause, 'Weak capacitor');
  assert.equal(m.agent.calls, 1);
  assert.ok(m.costUsd > 0);
});

test('part locator clamps the box to 0-1000', async () => {
  const r = await locatePart(fakeAI({ found: true, label: 'capacitor', box_2d: [-5, 100, 1200, 400] }), 'capacitor', 'FRAME');
  assert.deepEqual(r.box_2d, [0, 100, 1000, 400]);
});

test('step card returns the generated image', async () => {
  const m = newMetrics();
  const c = await stepCard(fakeAI({}), { instruction: 'Replace the capacitor', frameB64: 'FRAME' }, m);
  assert.equal(c.data, 'IMG');
  assert.equal(m.image.cards, 1);
});
