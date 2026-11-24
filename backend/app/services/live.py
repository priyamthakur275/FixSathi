"""Gemini Live relay. Browser <-> FastAPI WebSocket <-> Gemini Live (google-genai `client.aio.live.connect`).

The browser never sees the API key. Raw audio/video is not persisted; transcripts are.
Every model tool call is executed by this server. `give_step` goes through SafetyService.guard; the model cannot unlock safety.
"""
import asyncio, base64, binascii, contextlib, json, logging, time
from dataclasses import dataclass, field
from typing import Any, Callable
from google.genai import types
from sqlalchemy import func, select
from ..agents import prompts
from ..config import get_settings
from ..core.exceptions import AppError
from ..core.logging import log
from ..core.power_rules import MICROWAVE_ESCALATION, MICROWAVE_INTERNAL, POWER_WORDS, step_needs_power_off  # noqa: F401 - POWER_WORDS re-exported
from ..db.models import EscalationRequest, Media, RepairSession, RepairStep, User
from ..db.session import SessionLocal
from ..integrations.gemini.client import get_gemini
from ..integrations.storage.local import get_storage, inspect_image
from . import ai, safety
from .sessions import add_message, transition

logger = logging.getLogger('live')
SAFETY_NUDGE = ('[FixSaathi server notice] Your last spoken reply was withheld: it described power-sensitive work and the technician has '
                'not recorded the safety statements. Do not describe that work again. Ask the technician to switch off at the MCB, check '
                'with their own tester and tick both statements in the safety panel, then call request_safety_confirmation.')

TOOLS = [types.Tool(function_declarations=[
    types.FunctionDeclaration(name='get_diagnosis', description='Rank likely faults once the appliance and symptom are known.',
                              parameters_json_schema={'type': 'object', 'properties': {'appliance_type': {'type': 'string'}, 'symptom': {'type': 'string'}}, 'required': ['symptom']}),
    types.FunctionDeclaration(name='locate_part', description='Mark a named component on the latest camera frame.',
                              parameters_json_schema={'type': 'object', 'properties': {'part': {'type': 'string'}}, 'required': ['part']}),
    types.FunctionDeclaration(name='give_step', description='Deliver one repair step. The server decides whether it is allowed.',
                              parameters_json_schema={'type': 'object', 'properties': {'title': {'type': 'string'}, 'instruction': {'type': 'string'},
                                                      'requires_power_off': {'type': 'boolean'}}, 'required': ['title', 'instruction', 'requires_power_off']}),
    types.FunctionDeclaration(name='request_safety_confirmation', description='Ask the technician to record both safety statements in the app. Does not change safety state.',
                              parameters_json_schema={'type': 'object', 'properties': {}}),
    types.FunctionDeclaration(name='escalate_to_senior', description='Escalate to a senior technician.',
                              parameters_json_schema={'type': 'object', 'properties': {'reason': {'type': 'string'}}, 'required': ['reason']}),
])]


class LiveProtocolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message); self.code = code; self.message = message


@dataclass
class LiveContext:
    session_id: Any
    user_id: Any
    language: str = 'English'
    latest_frame: bytes | None = None
    user_text: list[str] = field(default_factory=list)
    model_text: list[str] = field(default_factory=list)


def default_connector(model: str, config: types.LiveConnectConfig):
    return get_gemini().raw.aio.live.connect(model=model, config=config)


Connector = Callable[[str, types.LiveConnectConfig], Any]
_connector: Connector = default_connector


def set_connector(c: Connector | None) -> None:
    global _connector
    _connector = c or default_connector


def build_config(language: str) -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        response_modalities=['AUDIO'], system_instruction=prompts.LIVE_SYSTEM.format(language=language), tools=TOOLS,
        input_audio_transcription=types.AudioTranscriptionConfig(), output_audio_transcription=types.AudioTranscriptionConfig(),
        context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()))


def decode_b64(data: Any, limit: int, what: str) -> bytes:
    if not isinstance(data, str) or len(data) > limit * 4 // 3 + 8:
        raise LiveProtocolError('PAYLOAD_TOO_LARGE' if isinstance(data, str) else 'INVALID_PAYLOAD', f'{what} is too large or malformed.')
    try:
        return base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        raise LiveProtocolError('INVALID_PAYLOAD', f'{what} is not valid base64.')


def parse_client(raw: str) -> dict:
    try:
        m = json.loads(raw)
    except json.JSONDecodeError:
        raise LiveProtocolError('INVALID_JSON', 'Messages must be JSON.')
    if not isinstance(m, dict) or m.get('type') not in ('audio_chunk', 'video_frame', 'text_input', 'end_session', 'audio_stream_end'):
        raise LiveProtocolError('UNKNOWN_TYPE', 'Unknown message type.')
    return m


async def run_tool(ctx: LiveContext, name: str, args: dict, emit) -> dict:
    db = SessionLocal()
    try:
        s = db.get(RepairSession, ctx.session_id); u = db.get(User, ctx.user_id)
        if not s or not u or s.status in ('completed', 'cancelled'):
            return {'error': 'session closed'}
        if name == 'give_step':
            title = str(args.get('title', ''))[:160]; instr = str(args.get('instruction', ''))[:800]
            if s.appliance_type == 'microwave_oven' and MICROWAVE_INTERNAL.search(f'{title} {instr}'):
                safety.record_block(db, s, u, f'live_step:{title}', 'MICROWAVE_INTERNAL', 'ai_tool'); db.commit()
                await emit({'type': 'safety_blocked', 'step_title': title, 'allowed': False, 'reason': 'MICROWAVE_INTERNAL', 'missing': [],
                            'disclaimer': MICROWAVE_ESCALATION})
                return {'allowed': False, 'reason': 'MICROWAVE_INTERNAL', 'say': MICROWAVE_ESCALATION}
            # The server, not the model, decides if a step is power-sensitive.
            needs = bool(args.get('requires_power_off')) or step_needs_power_off(f'{title} {instr}')
            d = safety.guard(db, s, u, f'live_step:{title}', needs, actor='ai_tool')
            if not d.allowed:
                if s.status in ('active', 'diagnosing', 'guidance_in_progress'):
                    transition(s, 'awaiting_confirmation')
                db.commit()
                await emit({'type': 'safety_blocked', 'step_title': title, **d.as_dict()})
                return {'allowed': False, 'reason': d.reason, 'missing': d.missing,
                        'say': 'Ask the technician to switch off at the MCB, check with their own tester, and tick both statements in the safety panel.'}
            n = (db.scalar(select(func.max(RepairStep.step_number)).where(RepairStep.session_id == s.id)) or 0) + 1
            st = RepairStep(session_id=s.id, step_number=n, title=title or f'Step {n}', instruction=instr, kind='power_sensitive' if needs else 'safe_action',
                            requires_power_off=needs, source='live')
            db.add(st)
            if s.status in ('active', 'diagnosing', 'awaiting_confirmation'):
                transition(s, 'guidance_in_progress')
            db.commit()
            await emit({'type': 'step', 'step': {'id': str(st.id), 'step_number': n, 'title': st.title, 'instruction': instr, 'requires_power_off': needs}})
            return {'allowed': True, 'step_number': n}
        if name == 'request_safety_confirmation':
            stt = safety.current_state(db, s)
            await emit({'type': 'safety_confirmation_required', 'missing': stt.missing, 'disclaimer': safety.DISCLAIMER})
            return {'unlocked': stt.unlocked, 'missing': stt.missing, 'note': 'Only the technician can record these in the app.'}
        if name == 'get_diagnosis':
            symptom = str(args.get('symptom', ''))[:500]
            if s.appliance_type == 'unknown' and args.get('appliance_type') in ai.prompts.APPLIANCE_NOTES:
                s.appliance_type = args['appliance_type']
            add_message(db, s, 'user', symptom, 'voice_transcript', {'via': 'live_tool'})
            if not s.issue_description:
                s.issue_description = symptom
            d = await ai.diagnose(db, s); db.commit()
            await emit({'type': 'diagnosis', 'diagnosis': {'id': str(d.id), 'problem_summary': d.problem_summary, 'faults': d.faults}})
            return {'problem_summary': d.problem_summary, 'top_faults': [{'fault': f['fault'], 'confidence_estimate': f['confidence']} for f in d.faults[:3]],
                    'follow_up_questions': d.follow_up_questions, 'requires_escalation': d.requires_escalation}
        if name == 'locate_part':
            if not ctx.latest_frame:
                return {'found': False, 'note': 'No camera frame received yet.'}
            mime, ext, w, h = inspect_image(ctx.latest_frame)
            key = get_storage().put(ctx.latest_frame, ext, f'sessions/{s.id}')
            m = Media(session_id=s.id, uploaded_by=u.id, kind='capture', storage_key=key, mime_type=mime, size_bytes=len(ctx.latest_frame), width=w, height=h, meta={'via': 'live_locate_part'})
            db.add(m); db.flush()
            c = await ai.identify_component(db, s, m.id, str(args.get('part', ''))[:120]); db.commit()
            await emit({'type': 'part_located', 'media_id': str(m.id), 'url': f'/api/v1/media/{m.id}', **c.result})
            return {'found': c.result.get('found'), 'component_name': c.result.get('component_name'), 'explanation': c.result.get('explanation')}
        if name == 'escalate_to_senior':
            open_ = db.scalar(select(func.count()).select_from(EscalationRequest).where(EscalationRequest.session_id == s.id, EscalationRequest.status != 'resolved'))
            if not open_:
                db.add(EscalationRequest(session_id=s.id, technician_id=u.id, reason=str(args.get('reason', ''))[:1000] or 'Requested during live session', source='live'))
                if s.status != 'escalated':
                    transition(s, 'escalated')
            db.commit()
            await emit({'type': 'escalated', 'reason': args.get('reason')})
            return {'escalated': True}
        return {'error': f'unknown tool {name}'}
    except AppError as e:
        db.rollback(); return {'error': e.code, 'message': e.message}
    finally:
        db.close()


def _hold_output(ctx: LiveContext) -> bool:
    """Hold this turn's spoken output for screening? Yes while the safety gate is locked, and always for microwaves."""
    db = SessionLocal()
    try:
        s = db.get(RepairSession, ctx.session_id)
        return not s or s.appliance_type == 'microwave_oven' or not safety.current_state(db, s).unlocked
    finally:
        db.close()


def _screen_spoken(ctx: LiveContext, spoken: str) -> 'safety.Screened':
    db = SessionLocal()
    try:
        s = db.get(RepairSession, ctx.session_id); u = db.get(User, ctx.user_id)
        if not s:
            return safety.Screened(safety.LOCK_NOTE_VOICE, withheld=1, reason='SESSION_CLOSED')
        if not spoken:  # audio arrived without a transcript: it cannot be checked, so it is not played (fail closed)
            safety.record_block(db, s, u, 'live_reply:unscreened_audio', 'UNSCREENED_AUDIO', 'live'); db.commit()
            return safety.Screened(safety.LOCK_NOTE_VOICE, withheld=1, reason='UNSCREENED_AUDIO')
        r = safety.screen_text(db, s, u, spoken, actor='live', voice=True); db.commit()
        return r
    finally:
        db.close()


def save_transcripts(ctx: LiveContext) -> None:
    if not ctx.user_text and not ctx.model_text:
        return
    db = SessionLocal()
    try:
        s = db.get(RepairSession, ctx.session_id)
        if s:
            if ctx.user_text:
                add_message(db, s, 'user', ''.join(ctx.user_text).strip(), 'voice_transcript')
            if ctx.model_text:
                add_message(db, s, 'assistant', ''.join(ctx.model_text).strip(), 'voice_transcript', {'ai_generated': True})
            db.commit()
    finally:
        db.close(); ctx.user_text.clear(); ctx.model_text.clear()


async def relay(ctx: LiveContext, recv_client: Callable[[], Any], emit: Callable[[dict], Any]) -> None:
    """Runs one live conversation until the client ends it, disconnects, or an error occurs."""
    st = get_settings()
    model = get_gemini().model('live')
    inbound: asyncio.Queue = asyncio.Queue(maxsize=64)  # bounded: back-pressure instead of unbounded memory
    last_video = 0.0
    async with _connector(model, build_config(ctx.language)) as gs:
        await emit({'type': 'session_ready', 'model': model})
        log(logger, 'live_connected', session=str(ctx.session_id), model=model)

        async def from_client():
            nonlocal last_video
            while True:
                raw = await asyncio.wait_for(recv_client(), timeout=st.live_idle_timeout_seconds)
                if raw is None:
                    return
                try:
                    m = parse_client(raw)
                    t = m['type']
                    if t == 'end_session':
                        return
                    if t == 'audio_chunk':
                        b = decode_b64(m.get('data'), st.live_max_audio_chunk_bytes, 'Audio chunk')
                        if len(b) % 2:
                            raise LiveProtocolError('INVALID_AUDIO', 'Audio must be 16-bit PCM.')
                        await inbound.put(('audio', b))
                    elif t == 'audio_stream_end':
                        await inbound.put(('audio_end', None))
                    elif t == 'video_frame':
                        b = decode_b64(m.get('data'), st.live_max_frame_bytes, 'Video frame')
                        if not b.startswith(b'\xff\xd8'):
                            raise LiveProtocolError('INVALID_IMAGE', 'Video frames must be JPEG.')
                        ctx.latest_frame = b
                        now = time.monotonic()
                        if now - last_video < 1.0 / max(st.live_video_fps, 0.1) or inbound.qsize() > 48:
                            continue  # throttle and drop frames under pressure
                        last_video = now
                        await inbound.put(('video', b))
                    elif t == 'text_input':
                        text = str(m.get('text', ''))[:2000]
                        if text.strip():
                            await inbound.put(('text', text))
                except LiveProtocolError as e:
                    await emit({'type': 'error', 'code': e.code, 'message': e.message, 'fatal': False})

        async def to_gemini():
            while True:
                kind, b = await inbound.get()
                if kind == 'audio':
                    await gs.send_realtime_input(audio=types.Blob(data=b, mime_type='audio/pcm;rate=16000'))
                elif kind == 'audio_end':
                    await gs.send_realtime_input(audio_stream_end=True)
                elif kind == 'video':
                    await gs.send_realtime_input(video=types.Blob(data=b, mime_type='image/jpeg'))
                elif kind == 'text':
                    ctx.user_text.append(b)
                    await gs.send_realtime_input(text=b)

        # Spoken output cannot be recalled once played. While the safety gate is locked (and always for microwaves) each
        # model turn is held, its transcript screened by safety.screen_text, then released in order or withheld.
        turn: dict = {'hold': None, 'buf': [], 'text': [], 'audio': False}
        nudged = False

        async def out(ev: dict, model_text: str | None = None):
            if turn['hold'] is None:
                turn['hold'] = await asyncio.to_thread(_hold_output, ctx)
            is_model = model_text is not None or ev['type'] == 'audio_chunk'
            if model_text is not None:
                turn['text'].append(model_text)
            turn['audio'] |= ev['type'] == 'audio_chunk'
            if turn['hold']:
                turn['buf'].append((is_model, ev)); return
            if model_text is not None:
                ctx.model_text.append(model_text)
            await emit(ev)

        async def finish_turn(interrupted: bool = False):
            nonlocal nudged
            t = dict(turn); turn.update(hold=None, buf=[], text=[], audio=False)
            if not t['hold']:
                nudged = False; return
            spoken = ''.join(t['text']).strip()
            verdict = None if interrupted or not (spoken or t['audio']) else await asyncio.to_thread(_screen_spoken, ctx, spoken)
            release = not interrupted and (verdict is None or not (verdict.withheld or verdict.microwave_escalated))
            for is_model, ev in t['buf']:
                if release or not is_model:
                    await emit(ev)
            if release:
                ctx.model_text.extend(t['text']); nudged = False
            elif verdict is not None:  # interrupted turns are simply dropped: the technician talked over them
                ctx.model_text.append(verdict.text)
                await emit({'type': 'safety_blocked', 'step_title': 'Spoken reply withheld', 'allowed': False, 'reason': verdict.reason,
                            'missing': ['power_off_confirmed', 'tester_checked'] if (verdict.reason or '').startswith('SAFETY_') else [],
                            'disclaimer': safety.DISCLAIMER})
                await emit({'type': 'transcription', 'role': 'assistant', 'text': verdict.text})
                if not nudged:  # once per withheld streak, so a refusal cannot loop
                    nudged = True
                    await gs.send_realtime_input(text=SAFETY_NUDGE)

        async def from_gemini():
            while True:
                async for msg in gs.receive():
                    sc = msg.server_content
                    if sc:
                        if sc.input_transcription and sc.input_transcription.text:
                            ctx.user_text.append(sc.input_transcription.text)
                            await emit({'type': 'transcription', 'role': 'user', 'text': sc.input_transcription.text})
                        if sc.output_transcription and sc.output_transcription.text:
                            await out({'type': 'transcription', 'role': 'assistant', 'text': sc.output_transcription.text}, sc.output_transcription.text)
                        for p in (sc.model_turn.parts if sc.model_turn and sc.model_turn.parts else []):
                            if p.inline_data and p.inline_data.data and (p.inline_data.mime_type or '').startswith('audio/'):
                                await out({'type': 'audio_chunk', 'mime_type': p.inline_data.mime_type, 'data': base64.b64encode(p.inline_data.data).decode()})
                            elif p.text and not getattr(p, 'thought', False):
                                await out({'type': 'assistant_text', 'text': p.text}, p.text)
                        if sc.interrupted:
                            await finish_turn(interrupted=True)
                            await emit({'type': 'interrupted'})
                        if sc.turn_complete:
                            await finish_turn()
                            await asyncio.to_thread(save_transcripts, ctx)
                            await emit({'type': 'turn_complete'})
                    if msg.tool_call and msg.tool_call.function_calls:
                        responses = []
                        for fc in msg.tool_call.function_calls:
                            await out({'type': 'tool_call_status', 'name': fc.name, 'status': 'running'})
                            result = await run_tool(ctx, fc.name or '', dict(fc.args or {}), out)
                            await out({'type': 'tool_call_status', 'name': fc.name, 'status': 'done'})
                            responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response=result))
                        await gs.send_tool_response(function_responses=responses)
                    if msg.go_away:
                        await emit({'type': 'notice', 'code': 'GO_AWAY', 'message': 'The live model will close this connection soon.'})

        tasks = [asyncio.create_task(from_client()), asyncio.create_task(to_gemini()), asyncio.create_task(from_gemini())]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                if t.exception() and not isinstance(t.exception(), asyncio.CancelledError):
                    raise t.exception()
        finally:
            for t in tasks:
                t.cancel()
            for t in tasks:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await t
            await asyncio.to_thread(save_transcripts, ctx)
            log(logger, 'live_closed', session=str(ctx.session_id))
