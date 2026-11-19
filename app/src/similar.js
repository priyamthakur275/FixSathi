// "Similar past repairs": semantic search over finished jobs + the fault knowledge base.
// Uses Gemini embeddings when available; falls back to keyword overlap so it never fails.
// The same interface can later be backed by AlloyDB (ScaNN vector index + AI functions in SQL).
import { KB } from './agents.js';
import { config } from './config.js';

const STOP = new Set('the a an is are was of to and or in on at for with it this that hai ka ki ke se me ko nahi na'.split(' '));
export const tokens = (s = '') => String(s).toLowerCase().split(/[^a-z0-9ऀ-ॿ]+/).filter((w) => w.length > 1 && !STOP.has(w));

export function jobDoc(job) {
  const r = job.report || {};
  const text = [job.complaint, r.appliance, r.brand_model, r.fault_found, r.root_cause, (r.work_done || []).join('. '), (r.parts_used || []).join(', ')]
    .filter(Boolean)
    .join(' | ');
  return { id: job.id, source: 'repair', title: `${r.appliance || 'Repair'}: ${r.fault_found || job.complaint || ''}`.trim(), text, outcome: r.outcome || job.status };
}

export function kbDocs() {
  const out = [];
  for (const [key, e] of Object.entries(KB.appliances || {})) {
    for (const f of e.faults || []) {
      const text = [key, f.symptom, ...(f.causes || []).flatMap((c) => [c.cause, c.check])].filter(Boolean).join(' | ');
      out.push({ id: `kb:${key}:${f.id || out.length}`, source: 'knowledge', title: `${key.replace('_', ' ')}: ${f.symptom || ''}`, text });
    }
  }
  return out;
}

function lexical(query, docs) {
  const q = new Set(tokens(query));
  return docs.map((d) => {
    const t = tokens(d.text);
    if (!t.length || !q.size) return { ...d, score: 0 };
    const hit = t.filter((w) => q.has(w)).length;
    return { ...d, score: hit / Math.sqrt(t.length * q.size) };
  });
}

const cos = (a, b) => {
  let d = 0, x = 0, y = 0;
  for (let i = 0; i < a.length; i++) { d += a[i] * b[i]; x += a[i] * a[i]; y += b[i] * b[i]; }
  return d / (Math.sqrt(x * y) || 1);
};
const cache = new Map();
async function embed(ai, texts) {
  const need = texts.filter((t) => !cache.has(t));
  if (need.length) {
    const res = await ai.models.embedContent({ model: config.embedModel, contents: need });
    res.embeddings.forEach((e, i) => cache.set(need[i], e.values));
  }
  return texts.map((t) => cache.get(t));
}

export async function similarRepairs(ai, jobs, query, k = 5) {
  const docs = [...jobs.filter((j) => j.report).map(jobDoc), ...kbDocs()].filter((d) => d.text);
  let scored, method = 'keyword';
  if (ai && config.embedModel && query.trim()) {
    try {
      const [qv, ...dv] = await embed(ai, [query, ...docs.map((d) => d.text)]);
      scored = docs.map((d, i) => ({ ...d, score: cos(qv, dv[i]) }));
      method = 'gemini-embedding';
    } catch (err) {
      console.error('embedding failed, using keyword search:', err.message);
    }
  }
  scored ||= lexical(query, docs);
  const top = scored.filter((d) => d.score > 0).sort((a, b) => b.score - a.score).slice(0, k)
    .map(({ id, source, title, outcome, score, text }) => ({ id, source, title, outcome, score: Number(score.toFixed(3)), snippet: text.slice(0, 220) }));
  return { method, results: top };
}
