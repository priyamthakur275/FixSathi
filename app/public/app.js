// FixSaathi technician app: camera + mic -> server -> Gemini Live, and renders the agent's events.
const $ = (id) => document.getElementById(id);
const state = { ws: null, stream: null, micCtx: null, playCtx: null, playHead: 0, sources: [], muted: false, facing: 'environment', frameTimer: null, caption: '', captionTimer: null, steps: 0, code: '' };

// ---------- helpers ----------
const b64FromBuf = (buf) => {
  const bytes = new Uint8Array(buf);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
};
const bufFromB64 = (b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)).buffer;
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
function toast(text, ms = 2600) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = text;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), ms);
}
const send = (m) => state.ws?.readyState === 1 && state.ws.send(JSON.stringify(m));

// ---------- health / setup ----------
fetch('/api/health').then((r) => r.json()).then((h) => {
  if (h.rehearsal) document.body.insertAdjacentHTML('afterbegin', '<div style="background:#e37400;color:#fff;text-align:center;font-weight:700;padding:6px">REHEARSAL MODE: scripted responses, not real AI</div>');
  $('health').innerHTML = h.ai ? '<span class="chip green">● AI ready</span>' : '<span class="chip red">● Server has no Gemini API key</span>';
  if (h.accessCode) $('codeWrap').classList.remove('hidden');
}).catch(() => {});
for (const id of ['tech', 'customer', 'lang', 'code']) {
  const v = localStorage.getItem('fs_' + id);
  if (v) $(id).value = v;
}

$('startBtn').onclick = start;

async function start() {
  $('startBtn').disabled = true;
  for (const id of ['tech', 'customer', 'lang', 'code']) localStorage.setItem('fs_' + id, $(id).value);
  state.code = $('code').value.trim();
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      video: { facingMode: { ideal: state.facing }, width: { ideal: 1280 }, height: { ideal: 960 } },
    });
  } catch (err) {
    $('startBtn').disabled = false;
    return toast('Camera/mic permission needed: ' + err.message, 4000);
  }
  $('video').srcObject = state.stream;
  $('setup').classList.add('hidden');
  $('liveView').classList.remove('hidden');
  $('dock').classList.remove('hidden');
  try { await navigator.wakeLock?.request('screen'); } catch {}

  state.playCtx = new AudioContext({ sampleRate: 24000 });
  await startMic();
  connect();
}

// ---------- audio in ----------
async function startMic() {
  state.micCtx = new AudioContext();
  await state.micCtx.audioWorklet.addModule('/mic-worklet.js');
  const src = state.micCtx.createMediaStreamSource(state.stream);
  const node = new AudioWorkletNode(state.micCtx, 'mic-processor');
  const sink = state.micCtx.createGain();
  sink.gain.value = 0;
  src.connect(node).connect(sink).connect(state.micCtx.destination);
  node.port.onmessage = ({ data }) => {
    $('level').style.width = Math.min(100, data.level * 160) + '%';
    if (!state.muted) send({ type: 'audio', data: b64FromBuf(data.pcm) });
  };
}

// ---------- audio out ----------
function playPcm(b64) {
  const ctx = state.playCtx;
  if (ctx.state === 'suspended') ctx.resume();
  const i16 = new Int16Array(bufFromB64(b64));
  const f32 = new Float32Array(i16.length);
  for (let i = 0; i < i16.length; i++) f32[i] = i16[i] / 0x8000;
  const buf = ctx.createBuffer(1, f32.length, 24000);
  buf.copyToChannel(f32, 0);
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.connect(ctx.destination);
  state.playHead = Math.max(state.playHead, ctx.currentTime + 0.03);
  src.start(state.playHead);
  state.playHead += buf.duration;
  state.sources.push(src);
  src.onended = () => (state.sources = state.sources.filter((s) => s !== src));
}
function stopPlayback() {
  for (const s of state.sources) try { s.stop(); } catch {}
  state.sources = [];
  state.playHead = 0;
}

// ---------- video frames (1 fps) ----------
const frameCanvas = document.createElement('canvas');
function captureFrame() {
  const v = $('video');
  if (!v.videoWidth) return null;
  const w = 768, h = Math.round((v.videoHeight / v.videoWidth) * w);
  frameCanvas.width = w;
  frameCanvas.height = h;
  frameCanvas.getContext('2d').drawImage(v, 0, 0, w, h);
  return frameCanvas.toDataURL('image/jpeg', 0.65).split(',')[1];
}

// ---------- connection ----------
function connect() {
  const q = new URLSearchParams({ tech: $('tech').value || 'Technician', customer: $('customer').value, complaint: $('complaint').value, lang: $('lang').value, code: state.code });
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/live?${q}`);
  state.ws = ws;
  ws.onmessage = (e) => handle(JSON.parse(e.data));
  ws.onclose = () => {
    $('conn').className = 'chip red small';
    $('conn').textContent = '● Disconnected';
    clearInterval(state.frameTimer);
  };
  ws.onerror = () => toast('Connection problem. Check internet.');
}

function handle(m) {
  switch (m.type) {
    case 'ready':
      $('conn').className = 'chip green small';
      $('conn').textContent = '● Live';
      $('jobId').textContent = m.jobId;
      state.frameTimer = setInterval(() => { const f = captureFrame(); if (f) send({ type: 'frame', data: f }); }, 1000);
      break;
    case 'audio': playPcm(m.data); break;
    case 'interrupted': stopPlayback(); break;
    case 'transcript': addLog(m.role, m.text); if (m.role === 'fixsaathi') setCaption(m.text); break;
    case 'turnComplete': state.newTurn = true; clearTimeout(state.captionTimer); state.captionTimer = setTimeout(() => { state.caption = ''; $('caption').textContent = ''; }, 4000); break;
    case 'thinking': $('thinking').textContent = m.what ? '⏳ ' + m.what : ''; $('thinking').classList.toggle('hidden', !m.what); break;
    case 'safety': setSafety(m); break;
    case 'blocked': {
      const c = $('lockChip');
      c.classList.remove('blocked'); void c.offsetWidth; c.classList.add('blocked');
      toast('⛔ Step blocked: switch off power and check with tester first');
      break;
    }
    case 'diagnosis': showDiagnosis(m.diagnosis); $('thinking').classList.add('hidden'); break;
    case 'mark': showMark(m); $('thinking').classList.add('hidden'); break;
    case 'step': addStep(m.step); break;
    case 'escalated': toast('📞 Senior notified: ' + m.escalation.reason, 4000); addLog('fixsaathi', '[Escalated to senior] ' + m.escalation.reason); break;
    case 'report': $('thinking').classList.add('hidden'); showReport(m); break;
    case 'status': toast(m.text); break;
    case 'error': toast('⚠️ ' + m.message, 5000); $('conn').className = 'chip red small'; $('conn').textContent = '● ' + m.message.slice(0, 40); break;
  }
}

// ---------- UI renderers ----------
function setCaption(text) {
  clearTimeout(state.captionTimer);
  if (state.captionNew) { state.caption = ''; state.captionNew = false; }
  state.caption = (state.caption + text).slice(-220);
  $('caption').textContent = state.caption;
}
function addLog(role, text) {
  const log = $('log');
  const last = log.lastElementChild;
  const fresh = state.newTurn && role === 'fixsaathi';
  if (fresh) { state.newTurn = false; state.captionNew = true; }
  if (!fresh && last && last.dataset.role === role && Date.now() - Number(last.dataset.ts) < 4000) {
    last.textContent += text;
    last.dataset.ts = Date.now();
  } else {
    const d = document.createElement('div');
    d.className = 't ' + role;
    d.dataset.role = role;
    d.dataset.ts = Date.now();
    d.textContent = text;
    log.appendChild(d);
  }
  log.scrollTop = log.scrollHeight;
}
function setSafety(m) {
  const c = $('lockChip');
  if (m.confirmed) {
    c.className = 'chip green lock';
    c.textContent = '🔓 Safety confirmed: steps unlocked';
    toast('✅ Safety confirmed');
  } else {
    c.className = 'chip red lock';
    c.textContent = '🔒 Repair steps locked: confirm power off';
  }
}
function showDiagnosis(d) {
  $('diagCard').classList.remove('hidden');
  const color = { high: 'red', medium: 'amber', low: 'grey' };
  $('causes').innerHTML = (d.causes || []).map((c, i) => `<div class="cause"><span class="chip ${color[c.likelihood] || 'grey'} small">${i + 1}. ${esc(c.likelihood)}</span><div><b>${esc(c.cause)}</b><div class="small muted">${esc(c.check)}</div></div></div>`).join('');
  $('nextCheck').innerHTML = d.next_check ? `<b>Next check:</b> ${esc(d.next_check)}` : '';
  $('diagSrc').textContent = d.source === 'knowledge_base' ? 'Knowledge base' : 'Diagnosis agent';
}
function showMark(m) {
  $('markCard').classList.remove('hidden');
  $('markLabel').textContent = m.label || m.part;
  $('markImg').src = 'data:image/jpeg;base64,' + m.frame;
  const [y0, x0, y1, x1] = m.box_2d;
  Object.assign($('markBox').style, { top: y0 / 10 + '%', left: x0 / 10 + '%', height: (y1 - y0) / 10 + '%', width: (x1 - x0) / 10 + '%' });
  Object.assign($('markTag').style, { top: y0 / 10 + '%', left: x0 / 10 + '%' });
  $('markTag').textContent = m.label || m.part;
  $('markCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function addStep(step) {
  $('noSteps')?.remove();
  const list = $('steps');
  for (const li of list.children) li.classList.add('done');
  const li = document.createElement('li');
  li.innerHTML = `<span class="n">${esc(step.n)}</span><span>${esc(step.instruction)}</span>`;
  list.appendChild(li);
  $('stepCount').textContent = list.children.length;
}
function showReport({ jobId, report: r }) {
  $('rOutcome').textContent = (r.outcome || '').replace('_', ' ');
  $('rOutcome').className = 'chip ' + (r.outcome === 'fixed' ? 'green' : 'amber');
  const rows = [
    ['Job', jobId], ['Appliance', [r.appliance, r.brand_model].filter((x) => x && x !== 'Not recorded').join(' · ')], ['Complaint', r.complaint],
    ['Fault found', r.fault_found], ['Work done', (r.work_done || []).join('; ')], ['Parts used', (r.parts_used || []).join(', ') || 'None'],
    ['First-time fix', r.first_time_fix ? 'Yes' : 'No'], ['For customer', r.customer_summary],
  ];
  $('rBody').innerHTML = rows.map(([k, v]) => `<b>${esc(k)}</b><span>${esc(v || '-')}</span>`).join('');
  $('reportDlg').showModal();
}

// ---------- controls ----------
$('micBtn').onclick = () => {
  state.muted = !state.muted;
  $('micBtn').classList.toggle('off', state.muted);
  $('micBtn').textContent = state.muted ? '🔇' : '🎙️';
};
$('textIn').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.target.value.trim()) {
    const text = e.target.value.trim();
    send({ type: 'text', text });
    addLog('technician', text);
    e.target.value = '';
  }
});
$('flipBtn').onclick = async () => {
  state.facing = state.facing === 'environment' ? 'user' : 'environment';
  try {
    const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: state.facing } } });
    const old = state.stream.getVideoTracks()[0];
    state.stream.removeTrack(old); old.stop();
    state.stream.addTrack(s.getVideoTracks()[0]);
    $('video').srcObject = state.stream;
  } catch (err) { toast('Could not switch camera'); }
};
$('endBtn').onclick = () => {
  $('endBtn').disabled = true;
  $('thinking').textContent = '⏳ Writing the service report…';
  $('thinking').classList.remove('hidden');
  send({ type: 'end' });
};
