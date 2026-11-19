import { test } from 'node:test';
import assert from 'node:assert/strict';
const { newMetrics, addLiveUsage, addAgentUsage, addLatency } = await import('../src/metrics.js');

test('live usage is priced per modality', () => {
  const m = newMetrics();
  addLiveUsage(m, {
    promptTokensDetails: [{ modality: 'AUDIO', tokenCount: 1_000_000 }, { modality: 'VIDEO', tokenCount: 1_000_000 }],
    responseTokensDetails: [{ modality: 'AUDIO', tokenCount: 1_000_000 }],
  });
  // 3 (audio in) + 1 (video in) + 12 (audio out) USD
  assert.equal(m.costUsd, 16);
  assert.ok(m.costInr > 0);
});

test('agent usage adds to cost', () => {
  const m = newMetrics();
  addAgentUsage(m, { promptTokenCount: 1_000_000, candidatesTokenCount: 1_000_000 });
  assert.equal(m.costUsd, 4.5);
  assert.equal(m.agent.calls, 1);
});

test('latency average ignores impossible values', () => {
  const m = newMetrics();
  addLatency(m, 800); addLatency(m, 1200); addLatency(m, -5); addLatency(m, 99999);
  assert.equal(m.avgLatencyMs, 1000);
});
