// REHEARSAL MODE (REHEARSAL=1): a scripted stand-in for Gemini, used only to test the UI,
// dashboard and tool pipeline without an API key or internet. The app shows a clear
// "Rehearsal mode" banner. Never present this as the real AI.
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const SCRIPT = [
  { say: 'Namaste! Main FixSaathi hoon. Kaunsa appliance hai aur kya problem hai?' },
  { tool: 'get_diagnosis', args: { appliance: 'ceiling fan', symptom: 'fan runs slow', observations: 'Ceiling fan visible' } },
  { say: 'Sabse common reason weak capacitor hai. Pehle safety: fan aur MCB off karo, tester se check karo.' },
  { tool: 'give_step', args: { step_number: 1, instruction: 'Open the canopy cover', needs_power_off: true } },
  { say: 'Ruko, pehle power off confirm karo. Tester lagao.' },
  { tool: 'confirm_safety', args: { power_off_confirmed: true, tester_checked: true, checks: ['Fan switch off', 'MCB off', 'Line tester shows no live wire'] } },
  { tool: 'give_step', args: { step_number: 1, instruction: 'Open the canopy cover and find the black capacitor', needs_power_off: true } },
  { tool: 'give_step', args: { step_number: 2, instruction: 'Replace it with the same rating capacitor (2.5 uF)', needs_power_off: true } },
  { say: 'Shabash. Ab power on karke speed check karo.' },
  { tool: 'complete_job', args: { outcome: 'fixed', fault_found: 'Weak fan capacitor', parts_replaced: ['2.5 uF fan capacitor'] } },
  { say: 'Report manager ko bhej di hai. Bahut badhiya kaam!' },
];

export function rehearsalAI() {
  return {
    models: { generateContent: async () => { throw new Error('rehearsal mode: using knowledge-base fallback'); } },
    live: {
      connect: async ({ callbacks }) => {
        let started = false;
        let closed = false;
        const pending = [];
        const session = {
          sendRealtimeInput: async (input) => {
            if (started || !input.text) return;
            started = true;
            for (const s of SCRIPT) {
              if (closed) return;
              await wait(1200);
              if (s.say) {
                callbacks.onmessage({ serverContent: { outputTranscription: { text: s.say } } });
                callbacks.onmessage({ serverContent: { turnComplete: true } });
              } else {
                const done = new Promise((r) => pending.push(r));
                callbacks.onmessage({ toolCall: { functionCalls: [{ id: String(Math.random()), name: s.tool, args: s.args }] } });
                await done;
              }
            }
          },
          sendToolResponse: () => pending.shift()?.(),
          close: () => { closed = true; },
        };
        setTimeout(() => callbacks.onopen?.(), 0);
        return session;
      },
    },
  };
}
