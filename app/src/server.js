// FixSaathi server: serves the apps, relays live audio/video to Gemini Live, runs the agents.
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import express from 'express';
import { WebSocketServer } from 'ws';
import { GoogleGenAI, Modality } from '@google/genai';
import { config } from './config.js';
import { liveSystemInstruction } from './prompts.js';
import { RepairSession, toolDeclarations } from './session.js';
import { store, events, summary } from './store.js';
import { rehearsalAI } from './rehearsal.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const rehearsal = process.env.REHEARSAL === '1';
const hasCreds = Boolean(config.apiKey || config.useVertex);
const ai = rehearsal
  ? rehearsalAI()
  : hasCreds
    ? new GoogleGenAI(config.useVertex ? { vertexai: true, project: config.project, location: config.location } : { apiKey: config.apiKey })
    : null;

const app = express();
app.use(express.json({ limit: '2mb' }));

const allowed = (code) => !config.accessCode || code === config.accessCode;
app.use('/api', (req, res, next) => {
  if (req.path === '/health' || allowed(req.query.code || req.get('x-access-code'))) return next();
  res.status(401).json({ error: 'Access code required' });
});

app.get('/api/health', (_req, res) =>
  res.json({ ok: true, ai: hasCreds || rehearsal, rehearsal, mode: config.useVertex ? 'vertex' : 'gemini-api', liveModels: config.liveModels, agentModel: config.agentModel, store: config.store, accessCode: Boolean(config.accessCode) }),
);
app.get('/api/jobs', async (_req, res) => res.json((await store.list(100)).map(summary)));
app.get('/api/jobs/:id', async (req, res) => {
  const job = await store.get(req.params.id);
  job ? res.json(job) : res.status(404).json({ error: 'Not found' });
});
// Live feed for the manager dashboard (Server-Sent Events).
app.get('/api/events', (req, res) => {
  res.set({ 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive' });
  res.flushHeaders();
  const send = (job) => res.write(`data: ${JSON.stringify(job)}\n\n`);
  const ping = setInterval(() => res.write(': ping\n\n'), 20000);
  events.on('job', send);
  req.on('close', () => { clearInterval(ping); events.off('job', send); });
});

app.use(express.static(path.join(here, '..', 'public'), { extensions: ['html'] }));

const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/live', maxPayload: 4 * 1024 * 1024 });

// Connect to Gemini Live, trying each configured model until one works.
async function connectLive(session, callbacks, resumeHandle) {
  let lastErr;
  for (const model of config.liveModels) {
    try {
      const live = await ai.live.connect({
        model,
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: liveSystemInstruction({ language: session.job.language, technician: session.technician }),
          speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: config.voice } } },
          tools: [{ functionDeclarations: toolDeclarations }],
          inputAudioTranscription: {},
          outputAudioTranscription: {},
          contextWindowCompression: { slidingWindow: {} }, // keeps long video sessions alive
          sessionResumption: resumeHandle ? { handle: resumeHandle } : {},
        },
        callbacks,
      });
      console.log(`[live] connected with ${model}`);
      return { live, model };
    } catch (err) {
      lastErr = err;
      console.warn(`[live] ${model} failed: ${err.message}`);
    }
  }
  throw lastErr || new Error('No live model configured');
}

wss.on('connection', async (ws, req) => {
  const url = new URL(req.url, 'http://x');
  const send = (msg) => ws.readyState === 1 && ws.send(JSON.stringify(msg));
  if (!allowed(url.searchParams.get('code'))) {
    send({ type: 'error', message: 'Wrong access code.' });
    return ws.close();
  }
  if (!ai) {
    send({ type: 'error', message: 'Server has no GEMINI_API_KEY. Add it and restart (see SETUP.md).' });
    return ws.close();
  }

  const session = new RepairSession({
    ai,
    technician: url.searchParams.get('tech') || 'Technician',
    customer: url.searchParams.get('customer') || '',
    complaint: url.searchParams.get('complaint') || '',
    language: url.searchParams.get('lang') === 'english' ? 'english' : 'hinglish',
    emit: send,
  });

  let live = null;
  let resumeHandle = null;
  let clientOpen = true;
  let reconnecting = false;

  const callbacks = {
    onopen: () => {},
    onmessage: async (msg) => {
      const sc = msg.serverContent;
      if (sc?.modelTurn?.parts) {
        for (const p of sc.modelTurn.parts) if (p.inlineData?.data) send({ type: 'audio', data: p.inlineData.data });
      }
      if (sc?.inputTranscription?.text) {
        session.addTranscript('technician', sc.inputTranscription.text);
        send({ type: 'transcript', role: 'technician', text: sc.inputTranscription.text });
      }
      if (sc?.outputTranscription?.text) {
        session.addTranscript('fixsaathi', sc.outputTranscription.text);
        send({ type: 'transcript', role: 'fixsaathi', text: sc.outputTranscription.text });
      }
      if (sc?.interrupted) send({ type: 'interrupted' });
      if (sc?.turnComplete) { session.endTurn(); send({ type: 'turnComplete' }); }
      if (msg.sessionResumptionUpdate?.resumable && msg.sessionResumptionUpdate.newHandle) resumeHandle = msg.sessionResumptionUpdate.newHandle;
      if (msg.goAway) console.log('[live] goAway, will resume', msg.goAway.timeLeft);

      if (msg.toolCall?.functionCalls?.length) {
        const responses = [];
        for (const fc of msg.toolCall.functionCalls) {
          send({ type: 'tool', name: fc.name, args: fc.args });
          const result = await session.handleTool(fc.name, fc.args || {});
          responses.push({ id: fc.id, name: fc.name, response: result });
        }
        try { live?.sendToolResponse({ functionResponses: responses }); } catch (e) { console.error('tool response failed', e.message); }
      }
    },
    onerror: (e) => console.error('[live] error', e?.message || e),
    onclose: async (e) => {
      console.log('[live] closed', e?.code, e?.reason || '');
      // Gemini ended the session (time limit / goAway) while the technician is still connected: resume.
      if (clientOpen && !reconnecting && resumeHandle) {
        reconnecting = true;
        try {
          ({ live } = await connectLive(session, callbacks, resumeHandle));
          send({ type: 'status', text: 'Reconnected' });
        } catch (err) {
          send({ type: 'error', message: 'Live session ended. Tap Start again.' });
        } finally { reconnecting = false; }
      } else if (clientOpen && !reconnecting) {
        send({ type: 'error', message: `Live session closed${e?.reason ? ': ' + e.reason : ''}. Tap Start again.` });
      }
    },
  };

  try {
    const r = await connectLive(session, callbacks);
    live = r.live;
    send({ type: 'ready', jobId: session.job.id, model: r.model });
    session.persist();
    // Kick off the conversation so FixSaathi greets first.
    live.sendRealtimeInput({ text: session.job.complaint ? `Start. Technician says the complaint is: ${session.job.complaint}` : 'Start the session. Greet me.' });
  } catch (err) {
    send({ type: 'error', message: 'Could not connect to Gemini Live: ' + err.message });
    return ws.close();
  }

  ws.on('message', async (raw) => {
    let m;
    try { m = JSON.parse(raw); } catch { return; }
    try {
      if (m.type === 'audio') live?.sendRealtimeInput({ audio: { data: m.data, mimeType: 'audio/pcm;rate=16000' } });
      else if (m.type === 'frame') { session.addFrame(m.data); live?.sendRealtimeInput({ video: { data: m.data, mimeType: 'image/jpeg' } }); }
      else if (m.type === 'text' && m.text) { session.addTranscript('technician', m.text); live?.sendRealtimeInput({ text: m.text }); }
      else if (m.type === 'end') {
        if (!session.job.report) await session.complete({ outcome: m.outcome || 'fixed', fault_found: m.fault || 'See transcript', notes: 'Ended from app' });
      }
    } catch (err) {
      console.error('client message failed', err.message);
    }
  });

  ws.on('close', () => {
    clientOpen = false;
    try { live?.close(); } catch {}
    if (!session.job.report) {
      session.job.status = session.job.status === 'escalated' ? 'escalated' : 'interrupted';
      session.persist();
    }
  });
});

server.listen(config.port, () => {
  console.log(`FixSaathi running on http://localhost:${config.port}  (AI: ${rehearsal ? 'REHEARSAL MODE (scripted, not real AI)' : hasCreds ? 'on' : 'OFF - set GEMINI_API_KEY'})`);
});
