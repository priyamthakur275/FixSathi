// One repair session = one job. Holds state, enforces the safety gate and runs tools.
import crypto from 'node:crypto';
import { diagnose, locatePart, writeReport } from './agents.js';
import { store } from './store.js';

const S = 'STRING', O = 'OBJECT', B = 'BOOLEAN', A = 'ARRAY', I = 'INTEGER';

// Tools the live agent can call. Declared for Gemini Live function calling.
export const toolDeclarations = [
  {
    name: 'confirm_safety',
    description:
      'Call ONLY after the technician has clearly confirmed power is off at the appliance AND MCB, and a line tester shows no live wire. Unlocks repair steps.',
    parameters: {
      type: O,
      properties: {
        power_off_confirmed: { type: B, description: 'Technician confirmed appliance and MCB are off' },
        tester_checked: { type: B, description: 'Technician confirmed with a line tester that no line is live' },
        checks: { type: A, items: { type: S }, description: 'Safety checks the technician confirmed, in English' },
      },
      required: ['power_off_confirmed', 'tester_checked', 'checks'],
    },
  },
  {
    name: 'get_diagnosis',
    description: 'Ask the diagnosis agent for ranked likely causes and the next check.',
    parameters: {
      type: O,
      properties: {
        appliance: { type: S, description: 'e.g. ceiling fan, split AC, MCB tripping, washing machine, refrigerator' },
        brand_model: { type: S },
        symptom: { type: S, description: 'Symptom in English' },
        observations: { type: S, description: 'What you see on camera' },
      },
      required: ['appliance', 'symptom'],
    },
  },
  {
    name: 'locate_part',
    description: 'Mark a specific part on the technician\'s screen using the latest camera frame.',
    parameters: {
      type: O,
      properties: { part: { type: S, description: 'Part name in English, e.g. "fan capacitor", "AC air filter"' } },
      required: ['part'],
    },
  },
  {
    name: 'give_step',
    description:
      'Show one repair step on screen. Steps that touch wires, open covers or handle parts are BLOCKED until confirm_safety succeeds.',
    parameters: {
      type: O,
      properties: {
        step_number: { type: I },
        instruction: { type: S, description: 'One short action in English' },
        needs_power_off: { type: B, description: 'true if the step involves opening, touching wires or parts' },
      },
      required: ['step_number', 'instruction', 'needs_power_off'],
    },
  },
  {
    name: 'escalate_to_senior',
    description: 'Flag the job for a senior / certified technician (gas work, PCB, burnt wiring, low confidence).',
    parameters: {
      type: O,
      properties: { reason: { type: S } },
      required: ['reason'],
    },
  },
  {
    name: 'complete_job',
    description: 'Finish the job. Generates and sends the service report to the manager dashboard.',
    parameters: {
      type: O,
      properties: {
        outcome: { type: S, enum: ['fixed', 'partially_fixed', 'not_fixed', 'escalated'] },
        fault_found: { type: S },
        parts_replaced: { type: A, items: { type: S } },
        notes: { type: S },
      },
      required: ['outcome', 'fault_found'],
    },
  },
];

export class RepairSession {
  constructor({ ai, technician = 'Technician', customer = '', complaint = '', language = 'hinglish', emit = () => {} }) {
    this.ai = ai;
    this.emit = emit; // send an event to the technician's app
    this.job = {
      id: 'JOB-' + new Date().toISOString().slice(2, 10).replace(/-/g, '') + '-' + crypto.randomBytes(2).toString('hex').toUpperCase(),
      technician,
      customer,
      complaint,
      language,
      status: 'in_progress',
      createdAt: new Date().toISOString(),
      safety: { confirmed: false, checks: [], blockedAttempts: 0 },
      diagnosis: null,
      marks: [],
      steps: [],
      escalations: [],
      completion: null,
      report: null,
      photos: {},
      transcript: [],
    };
    this.latestFrame = null;
    this.savePending = null;
  }

  get technician() { return this.job.technician; }

  addFrame(b64) {
    this.latestFrame = b64;
    if (!this.job.photos.before) this.job.photos.before = b64;
  }

  addTranscript(role, text) {
    if (!text) return;
    const t = this.job.transcript;
    const last = t[t.length - 1];
    const fresh = this.turnEnded && role === 'fixsaathi';
    if (fresh) this.turnEnded = false;
    if (!fresh && last && last.role === role && Date.now() - last.ts < 4000) {
      last.text += text;
      last.ts = Date.now();
    } else t.push({ role, text, ts: Date.now() });
  }

  endTurn() { this.turnEnded = true; }

  // Debounced save so the manager dashboard sees live progress.
  persist() {
    clearTimeout(this.savePending);
    this.savePending = setTimeout(() => store.save(this.job).catch((e) => console.error('save failed', e.message)), 400);
  }

  async handleTool(name, args = {}) {
    try {
      const out = await this.#run(name, args);
      this.persist();
      return out;
    } catch (err) {
      console.error(`tool ${name} failed:`, err);
      return { error: `Tool failed: ${err.message}. Continue guiding without it.` };
    }
  }

  async #run(name, args) {
    const job = this.job;
    switch (name) {
      case 'confirm_safety': {
        if (!args.power_off_confirmed || !args.tester_checked) {
          this.emit({ type: 'safety', confirmed: false });
          return {
            confirmed: false,
            message: 'NOT CONFIRMED. Ask the technician to switch off the appliance and the MCB, and check with a line tester. Do not continue until both are confirmed.',
          };
        }
        job.safety = { ...job.safety, confirmed: true, checks: args.checks || [], at: new Date().toISOString() };
        this.emit({ type: 'safety', confirmed: true, checks: job.safety.checks });
        return { confirmed: true, message: 'Safety confirmed. Repair steps are unlocked.' };
      }
      case 'get_diagnosis': {
        this.emit({ type: 'thinking', what: 'Diagnosis agent is analysing…' });
        const d = await diagnose(this.ai, args, this.latestFrame);
        job.diagnosis = { ...args, ...d, at: new Date().toISOString() };
        if (!job.complaint) job.complaint = args.symptom;
        this.emit({ type: 'diagnosis', diagnosis: job.diagnosis });
        return d;
      }
      case 'locate_part': {
        this.emit({ type: 'thinking', what: `Locating ${args.part}…` });
        const r = await locatePart(this.ai, args.part, this.latestFrame);
        if (r.found) {
          const mark = { part: args.part, label: r.label, box_2d: r.box_2d, frame: this.latestFrame };
          job.marks.push({ part: args.part, label: r.label, box_2d: r.box_2d });
          this.emit({ type: 'mark', ...mark });
          return { found: true, message: `Marked "${r.label}" on the technician's screen.` };
        }
        this.emit({ type: 'thinking', what: '' });
        return { found: false, message: `Could not see the ${args.part}. Ask the technician to move the camera closer or add light.` };
      }
      case 'give_step': {
        if (args.needs_power_off && !job.safety.confirmed) {
          job.safety.blockedAttempts++;
          this.emit({ type: 'blocked', instruction: args.instruction });
          return {
            blocked: true,
            message: 'BLOCKED by safety agent: power-off and tester check not confirmed yet. Do NOT give this step. Ask the technician to switch off the appliance and MCB and check with a tester first.',
          };
        }
        const step = { n: args.step_number || job.steps.length + 1, instruction: args.instruction, at: new Date().toISOString() };
        job.steps.push(step);
        this.emit({ type: 'step', step });
        return { shown: true, message: 'Step shown. Wait for the technician to finish it before the next step.' };
      }
      case 'escalate_to_senior': {
        const e = { reason: args.reason, at: new Date().toISOString() };
        job.escalations.push(e);
        job.status = 'escalated';
        this.emit({ type: 'escalated', escalation: e });
        return { escalated: true, message: 'A senior has been notified on the manager dashboard.' };
      }
      case 'complete_job': {
        return this.complete(args);
      }
      default:
        return { error: `Unknown tool ${name}` };
    }
  }

  async complete(args = {}) {
    const job = this.job;
    if (job.report) return { done: true, message: 'Report already sent.' };
    job.completion = { ...args, at: new Date().toISOString() };
    if (this.latestFrame) job.photos.after = this.latestFrame;
    this.emit({ type: 'thinking', what: 'Report agent is writing the service report…' });
    job.report = await writeReport(this.ai, job);
    job.status = job.escalations.length ? 'escalated' : job.report.outcome === 'fixed' ? 'completed' : job.report.outcome;
    job.completedAt = new Date().toISOString();
    clearTimeout(this.savePending);
    await store.save(job);
    this.emit({ type: 'report', jobId: job.id, report: job.report });
    return { done: true, message: 'Service report saved and sent to the manager dashboard.' };
  }
}
