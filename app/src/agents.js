// Gemini API agents: diagnosis, part locator and report writer.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DIAGNOSIS_PROMPT, REPORT_PROMPT, LOCATE_PROMPT } from './prompts.js';
import { config } from './config.js';

const here = path.dirname(fileURLToPath(import.meta.url));
export const KB = JSON.parse(fs.readFileSync(path.join(here, '..', 'knowledge', 'faults.json'), 'utf8'));

// Pick the knowledge-base section that matches the appliance name.
export function kbFor(appliance = '') {
  const a = appliance.toLowerCase();
  for (const [key, entry] of Object.entries(KB.appliances)) {
    if (a.includes(key.replace('_', ' ')) || entry.aliases.some((x) => a.includes(x))) return { key, ...entry };
  }
  return null;
}

async function jsonCall(ai, { system, parts, schema }) {
  const res = await ai.models.generateContent({
    model: config.agentModel,
    contents: [{ role: 'user', parts }],
    config: {
      systemInstruction: system,
      responseMimeType: 'application/json',
      responseJsonSchema: schema,
      temperature: 0.2,
    },
  });
  return JSON.parse(res.text);
}

const diagnosisSchema = {
  type: 'object',
  properties: {
    causes: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          cause: { type: 'string' },
          likelihood: { type: 'string', enum: ['high', 'medium', 'low'] },
          check: { type: 'string' },
        },
        required: ['cause', 'likelihood', 'check'],
      },
    },
    next_check: { type: 'string' },
    escalate: { type: 'boolean', description: 'true if this needs a senior / certified technician' },
  },
  required: ['causes', 'next_check', 'escalate'],
};

export async function diagnose(ai, { appliance, brand_model, symptom, observations }, frameB64) {
  const kb = kbFor(appliance);
  const parts = [
    {
      text: JSON.stringify({
        appliance,
        brand_model: brand_model || 'unknown',
        symptom,
        observations: observations || '',
        knowledge_base: kb ? kb.faults : 'No KB entry; use general expertise.',
        safety_rules: KB.safety_rules,
      }),
    },
  ];
  if (frameB64) parts.push({ inlineData: { mimeType: 'image/jpeg', data: frameB64 } });
  try {
    return await jsonCall(ai, { system: DIAGNOSIS_PROMPT, parts, schema: diagnosisSchema });
  } catch (err) {
    // Fallback: knowledge base only, so the demo never dead-ends.
    console.error('diagnosis agent failed, using KB fallback:', err.message);
    const s = (symptom || '').toLowerCase();
    const fault = kb?.faults.find((f) => f.symptom.split(/[ /]+/).some((w) => w.length > 3 && s.includes(w))) || kb?.faults[0];
    return fault
      ? { causes: fault.causes.slice(0, 3), next_check: fault.causes[0].check, escalate: false, source: 'knowledge_base' }
      : { causes: [], next_check: 'Describe the symptom again and show the label.', escalate: false, source: 'none' };
  }
}

const locateSchema = {
  type: 'object',
  properties: {
    found: { type: 'boolean' },
    label: { type: 'string' },
    box_2d: { type: 'array', items: { type: 'integer' }, minItems: 4, maxItems: 4 },
  },
  required: ['found', 'label'],
};

export async function locatePart(ai, part, frameB64) {
  if (!frameB64) return { found: false, label: part, reason: 'No camera frame yet' };
  const out = await jsonCall(ai, {
    system: 'You locate parts in photos of appliances. Be precise.',
    parts: [{ inlineData: { mimeType: 'image/jpeg', data: frameB64 } }, { text: LOCATE_PROMPT(part) }],
    schema: locateSchema,
  });
  if (out.found && Array.isArray(out.box_2d) && out.box_2d.length === 4) {
    out.box_2d = out.box_2d.map((v) => Math.max(0, Math.min(1000, Math.round(v))));
  } else out.found = false;
  return out;
}

const reportSchema = {
  type: 'object',
  properties: {
    appliance: { type: 'string' },
    brand_model: { type: 'string' },
    complaint: { type: 'string' },
    fault_found: { type: 'string' },
    root_cause: { type: 'string' },
    work_done: { type: 'array', items: { type: 'string' } },
    parts_used: { type: 'array', items: { type: 'string' } },
    safety_checks: { type: 'array', items: { type: 'string' } },
    outcome: { type: 'string', enum: ['fixed', 'partially_fixed', 'not_fixed', 'escalated'] },
    first_time_fix: { type: 'boolean' },
    follow_up: { type: 'string' },
    customer_summary: { type: 'string', description: 'Two simple sentences for the customer' },
  },
  required: ['appliance', 'complaint', 'fault_found', 'work_done', 'outcome', 'first_time_fix', 'customer_summary'],
};

export async function writeReport(ai, session) {
  const data = {
    technician: session.technician,
    customer: session.customer,
    complaint: session.complaint,
    safety: session.safety,
    diagnosis: session.diagnosis,
    steps: session.steps,
    escalations: session.escalations,
    completion: session.completion,
    transcript: session.transcript.slice(-120),
  };
  try {
    return await jsonCall(ai, { system: REPORT_PROMPT, parts: [{ text: JSON.stringify(data) }], schema: reportSchema });
  } catch (err) {
    console.error('report agent failed, using structured fallback:', err.message);
    const c = session.completion || {};
    return {
      appliance: c.appliance || session.diagnosis?.appliance || 'Not recorded',
      brand_model: c.brand_model || 'Not recorded',
      complaint: session.complaint || 'Not recorded',
      fault_found: c.fault_found || 'Not recorded',
      root_cause: c.fault_found || 'Not recorded',
      work_done: session.steps.map((s) => s.instruction),
      parts_used: c.parts_replaced || [],
      safety_checks: session.safety.checks || [],
      outcome: c.outcome || 'fixed',
      first_time_fix: (c.outcome || 'fixed') === 'fixed',
      follow_up: c.notes || '',
      customer_summary: 'The appliance was inspected and serviced. Please contact us if the problem returns.',
    };
  }
}
