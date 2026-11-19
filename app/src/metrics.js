// Measured usage, cost and latency per repair job.
// Prices in USD per 1M tokens, from Google's published rates (override with env if they change).
const num = (k, d) => (process.env[k] !== undefined ? Number(process.env[k]) : d);
export const PRICES = {
  live: {
    audioIn: num('PRICE_LIVE_AUDIO_IN', 3.0),
    videoIn: num('PRICE_LIVE_VIDEO_IN', 1.0),
    textIn: num('PRICE_LIVE_TEXT_IN', 0.75),
    audioOut: num('PRICE_LIVE_AUDIO_OUT', 12.0),
    textOut: num('PRICE_LIVE_TEXT_OUT', 4.5),
  },
  agent: { in: num('PRICE_AGENT_IN', 0.75), out: num('PRICE_AGENT_OUT', 3.75) },
  // Image model price is not set by default; set PRICE_IMAGE_OUT to include step cards in cost.
  image: { in: num('PRICE_IMAGE_IN', 0), out: num('PRICE_IMAGE_OUT', 0) },
};
export const USD_INR = num('USD_INR', 88);

export function newMetrics() {
  return {
    live: { audioIn: 0, videoIn: 0, textIn: 0, audioOut: 0, textOut: 0 },
    agent: { in: 0, out: 0, calls: 0 },
    image: { in: 0, out: 0, cards: 0 },
    latencyMs: [],
    avgLatencyMs: null,
    costUsd: 0,
    costInr: 0,
  };
}

const key = { AUDIO: 'audio', VIDEO: 'video', IMAGE: 'video', TEXT: 'text' };

// Live API usage: prompt tokens are billed every turn (accumulated context), so we sum per message.
export function addLiveUsage(m, u) {
  if (!u) return;
  const add = (details, dir) => {
    let counted = 0;
    for (const d of details || []) {
      const k = (key[d.modality] || 'text') + dir;
      if (m.live[k] !== undefined) { m.live[k] += d.tokenCount || 0; counted += d.tokenCount || 0; }
    }
    return counted;
  };
  const pin = add(u.promptTokensDetails, 'In');
  if (!pin && u.promptTokenCount) m.live.textIn += u.promptTokenCount;
  const pout = add(u.responseTokensDetails, 'Out');
  if (!pout && u.responseTokenCount) m.live.audioOut += u.responseTokenCount;
  if (u.thoughtsTokenCount) m.live.textOut += u.thoughtsTokenCount;
  recompute(m);
}

export function addAgentUsage(m, u) {
  if (!u) return;
  m.agent.in += u.promptTokenCount || 0;
  m.agent.out += (u.candidatesTokenCount || 0) + (u.thoughtsTokenCount || 0);
  m.agent.calls++;
  recompute(m);
}

export function addImageUsage(m, u) {
  m.image.cards++;
  if (u) { m.image.in += u.promptTokenCount || 0; m.image.out += u.candidatesTokenCount || 0; }
  recompute(m);
}

export function addLatency(m, ms) {
  if (!(ms > 0 && ms < 30000)) return;
  m.latencyMs.push(Math.round(ms));
  if (m.latencyMs.length > 60) m.latencyMs.shift();
  m.avgLatencyMs = Math.round(m.latencyMs.reduce((a, b) => a + b, 0) / m.latencyMs.length);
}

export function recompute(m) {
  const L = PRICES.live, M = 1e6;
  const usd =
    (m.live.audioIn * L.audioIn + m.live.videoIn * L.videoIn + m.live.textIn * L.textIn + m.live.audioOut * L.audioOut + m.live.textOut * L.textOut) / M +
    (m.agent.in * PRICES.agent.in + m.agent.out * PRICES.agent.out) / M +
    (m.image.in * PRICES.image.in + m.image.out * PRICES.image.out) / M;
  m.costUsd = Number(usd.toFixed(5));
  m.costInr = Number((usd * USD_INR).toFixed(2));
}
