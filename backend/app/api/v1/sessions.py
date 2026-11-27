import asyncio, json, re, uuid
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session
from ...core.exceptions import AppError, NotFound
from ...core.quota import check_ai_quota
from ...demo.client import is_demo
from ...db.base import utcnow
from ...db.models import Conversation, Media, RepairSession, User
from ...db.session import SessionLocal, get_db
from ...dependencies import current_user
from ...integrations.storage.local import get_storage
from ...schemas.repair import AnswerFeedbackIn, ChatResult, MediaOut, MessageIn, MessageOut, Page, SessionCreate, SessionOut, SessionPatch
from ...services import ai, safety
from ...services.access import get_owned_session, get_readable_session, session_scope
from ...services.sessions import TERMINAL, add_message, chat_title, create_session, ensure_open, retitle_from, transition
from .serializers import media_out, session_out

router = APIRouter(tags=['sessions'])

_PDF_ASK = r'(?:generate|create|make|prepare|export|download|give|send|share|want|need|get)'
_PDF_INTENT = [re.compile(r'\bpdf\b.{0,40}\b(?:banao|bana do|banado|chahiye|do)\b', re.I),
               re.compile(rf'\b{_PDF_ASK}\b.{{0,50}}\bpdf\b', re.I),
               re.compile(r'\b(?:generate|create|make|prepare)\b.{0,40}\breport\b', re.I),
               re.compile(r'\b(?:download|export|save|print)\b.{0,40}\b(?:report|diagnosis|summary|instructions|steps|this|chat|conversation)\b', re.I),
               re.compile(r'\b(?:report|summary)\b.{0,20}\b(?:banao|bana do|banado|chahiye)\b', re.I)]
PDF_REPLY = ('Your repair report for this conversation is ready. It is built only from what is recorded in this session: the reported problem, '
             'diagnosis, repair steps, safety statements and escalations. Use **Download PDF** below.')


def wants_pdf(text: str) -> bool:
    """True when the technician asks for a report or PDF of this conversation, e.g. 'Generate a repair report PDF' or 'Download this diagnosis'."""
    t = ' '.join(text.split())
    return 0 < len(t) <= 200 and any(p.search(t) for p in _PDF_INTENT)


@router.post('/sessions', response_model=SessionOut, status_code=201)
def create(body: SessionCreate, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return session_out(db, create_session(db, u, body.appliance_type, body.issue_description, body.title))


@router.get('/sessions', response_model=Page)
def list_sessions(status: str | None = None, appliance_type: str | None = None, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                  q: str | None = Query(None, max_length=120, description='Search titles, issue text and messages'),
                  mine: bool = Query(False, description="Only the caller's own conversations (chat history), not the team's"),
                  u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """Conversations the technician deleted from their chat history are not listed; the records themselves are kept."""
    query = session_scope(u).where(RepairSession.hidden_at.is_(None))
    if mine:
        query = query.where(RepairSession.technician_id == u.id)
    if q and q.strip():
        like = '%' + re.sub(r'([%_\\])', r'\\\1', q.strip()) + '%'
        in_messages = exists().where(Conversation.session_id == RepairSession.id, Conversation.message.ilike(like, escape='\\'))
        query = query.where(or_(RepairSession.title.ilike(like, escape='\\'), RepairSession.issue_description.ilike(like, escape='\\'), in_messages))
    if status:
        query = query.where(RepairSession.status.in_(status.split(',')))
    if appliance_type:
        query = query.where(RepairSession.appliance_type == appliance_type)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(RepairSession.created_at.desc()).limit(limit).offset(offset)).unique().all()
    return Page(items=[session_out(db, s) for s in rows], total=total or 0, limit=limit, offset=offset)


@router.get('/sessions/{session_id}', response_model=SessionOut)
def get_session(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    return session_out(db, _open_chat(db, u, session_id))


def _open_chat(db: Session, u: User, session_id: uuid.UUID) -> RepairSession:
    """A deleted chat cannot be opened as a chat by anyone. Its work records (escalations, history, service reports) are kept."""
    s = get_readable_session(db, u, session_id)
    if s.hidden_at is not None:
        raise NotFound('Chat not found.')
    return s


@router.patch('/sessions/{session_id}', response_model=SessionOut)
def patch_session(session_id: uuid.UUID, body: SessionPatch, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id, lock=True)
    data = body.model_dump(exclude_none=True)
    if set(data) != {'title'}:  # renaming a conversation is allowed after it is closed; nothing else is
        ensure_open(s)
    if 'title' in data:
        data['title'] = ' '.join(data['title'].split()) or s.title
        s.appliance_details = {**(s.appliance_details or {}), 'title_auto': False}
    if 'status' in data:
        transition(s, data.pop('status'))
    for k, v in data.items():
        setattr(s, k, v)
    db.flush()
    return session_out(db, s)


@router.delete('/sessions/{session_id}', status_code=204)
def delete_conversation(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """Removes the conversation from the technician's chat history. Nothing is erased: service reports, the safety log and
    manager analytics keep their records. An open session is cancelled so it does not stay 'active' forever."""
    s = get_owned_session(db, u, session_id, lock=True)
    if s.status not in TERMINAL:
        transition(s, 'cancelled')
    s.hidden_at = s.hidden_at or utcnow()
    return Response(status_code=204)


@router.get('/sessions/{session_id}/report.pdf')
def report_pdf(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """A PDF of what is recorded for this conversation. Power-sensitive step instructions stay hidden unless the safety statements are recorded."""
    from urllib.parse import quote
    from ...services.pdf_report import render_session_pdf
    s = get_readable_session(db, u, session_id)
    data = render_session_pdf(db, s, u)
    name = f'FixSaathi-{s.reference}-repair-report.pdf'
    return Response(data, media_type='application/pdf', headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(name)}",
                                                                 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})


@router.post('/sessions/{session_id}/cancel', response_model=SessionOut)
def cancel(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_owned_session(db, u, session_id, lock=True); transition(s, 'cancelled')
    return session_out(db, s)


@router.get('/sessions/{session_id}/messages', response_model=Page)
def messages(session_id: uuid.UUID, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = _open_chat(db, u, session_id)
    q = select(Conversation).where(Conversation.session_id == s.id)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(Conversation.created_at).limit(limit).offset(offset)).all()
    return Page(items=[MessageOut.model_validate(r) for r in rows], total=total or 0, limit=limit, offset=offset)


def _prepare_user_message(db: Session, u: User, session_id: uuid.UUID, body: MessageIn) -> tuple[RepairSession, Conversation]:
    s = get_owned_session(db, u, session_id); ensure_open(s)
    if not body.text.strip() and not body.media_ids:
        raise AppError('Message is empty.', code='EMPTY_MESSAGE')
    files = []
    if body.media_ids:
        rows = {m.id: m for m in db.scalars(select(Media).where(Media.id.in_(body.media_ids), Media.session_id == s.id, Media.kind != 'generated'))}
        if set(rows) != set(body.media_ids):
            raise NotFound('One or more files do not belong to this session.')
        files = [{'id': str(i), 'kind': 'document' if rows[i].kind == 'document' else 'image', 'mime': rows[i].mime_type, 'size': rows[i].size_bytes,
                  'name': (rows[i].meta or {}).get('filename'), 'pages': (rows[i].meta or {}).get('pages')} for i in dict.fromkeys(body.media_ids)]
    mtype = ('image' if all(f['kind'] == 'image' for f in files) else 'file') if files and not body.text.strip() else 'text'
    um = add_message(db, s, 'user', body.text.strip(), mtype, {'media_ids': [str(i) for i in dict.fromkeys(body.media_ids)], 'attachments': files, 'channel': body.channel})
    if not s.issue_description and body.text.strip():
        s.issue_description = body.text.strip()[:2000]
        if (s.appliance_details or {}).get('title_auto'):  # e.g. a photo-only first message: name the chat after the first description
            s.title = chat_title(s.issue_description, s.appliance_type)
    elif body.text.strip():
        retitle_from(s, body.text)
    return s, um


def _sse(event: str, payload: dict) -> str:
    return f'event: {event}\ndata: {json.dumps(payload, default=str)}\n\n'


@router.post('/sessions/{session_id}/messages', response_model=ChatResult, status_code=201)
async def post_message(session_id: uuid.UUID, body: MessageIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s, um = _prepare_user_message(db, u, session_id, body)
    if not body.media_ids and wants_pdf(body.text):
        # Answered by the server, not Gemini: the PDF is built from recorded data, so there is nothing for the model to write.
        am = add_message(db, s, 'assistant', PDF_REPLY, meta={'action': 'pdf_report', 'ai_generated': False, 'channel': body.channel})
        return ChatResult(user_message=MessageOut.model_validate(um), assistant_message=MessageOut.model_validate(am), ai_status='ok')
    db.commit()  # persist the technician's message even if the AI call fails
    try:
        if not is_demo(s):
            check_ai_quota(u.id)
        am = await ai.chat_reply(db, s, u, body.text.strip(), body.media_ids, exclude_id=um.id, channel=body.channel)
        return ChatResult(user_message=MessageOut.model_validate(um), assistant_message=MessageOut.model_validate(am), ai_status='ok')
    except AppError as e:
        db.commit()
        return ChatResult(user_message=MessageOut.model_validate(um), assistant_message=None, ai_status='unavailable' if e.status == 503 else 'error',
                          ai_error={'code': e.code, 'message': e.message, 'hint': e.details.get('hint'), 'provider_status': e.details.get('provider_status')})


@router.post('/sessions/{session_id}/messages/stream')
async def stream_message(request: Request, session_id: uuid.UUID, body: MessageIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """Stream AI reply via SSE with sentence-by-sentence server safety screening before any text reaches the client."""
    s, um = _prepare_user_message(db, u, session_id, body)
    text = body.text.strip()
    media_ids = list(body.media_ids)
    channel = body.channel
    pdf_fast = not media_ids and wants_pdf(text)
    if not pdf_fast and not is_demo(s):
        check_ai_quota(u.id)
    um_json = MessageOut.model_validate(um).model_dump(mode='json')
    sid, uid, um_id = s.id, u.id, um.id
    db.commit()

    async def event_stream():
        yield _sse('user_message', {'user_message': um_json})
        if pdf_fast:
            with SessionLocal() as sdb:
                sess = sdb.get(RepairSession, sid)
                am = add_message(sdb, sess, 'assistant', PDF_REPLY, meta={'action': 'pdf_report', 'ai_generated': False, 'channel': channel})
                sdb.commit()
                am_json = MessageOut.model_validate(am).model_dump(mode='json')
            yield _sse('delta', {'text': PDF_REPLY})
            yield _sse('done', {'assistant_message': am_json, 'ai_status': 'ok'})
            return

        with SessionLocal() as sdb:
            sess = sdb.get(RepairSession, sid)
            usr = sdb.get(User, uid)
            try:
                g, res, contents, system, allowed = await ai.prepare_chat_stream(sdb, sess, usr, text, media_ids, exclude_id=um_id, channel=channel)
                used_cites: list[str] = []
                invented_cites: list[str] = []

                def clean_fn(txt: str) -> str:
                    cleaned, u_ids, inv_ids = ai._clean_citations(txt, allowed)
                    used_cites.extend(u_ids)
                    invented_cites.extend(inv_ids)
                    return cleaned

                screener = safety.StreamScreener(sdb, sess, usr, actor='chat', voice=channel == 'voice', cite_fn=clean_fn)
                meta = None
                async for chunk, call_meta in g.stream_text('chat', contents, system):
                    if await request.is_disconnected():
                        sdb.rollback()
                        return
                    if chunk:
                        for part in screener.feed(chunk):
                            yield _sse('delta', {'text': part})
                    if call_meta is not None:
                        meta = call_meta
                if await request.is_disconnected():
                    sdb.rollback()
                    return
                for part in screener.finish():
                    yield _sse('delta', {'text': part})
                if await request.is_disconnected():
                    sdb.rollback()
                    return
                am = ai.finalize_stream_message(sdb, sess, meta, res, list(dict.fromkeys(used_cites)), invented_cites, screener, channel)
                sdb.commit()
                am_json = MessageOut.model_validate(am).model_dump(mode='json')
                yield _sse('done', {'assistant_message': am_json, 'ai_status': 'ok'})
            except asyncio.CancelledError:
                sdb.rollback()
                return
            except AppError as e:
                sdb.rollback()
                sess_err = sdb.get(RepairSession, sid)
                ai.record_usage(sdb, sess_err, 'chat', None, ok=False, code=e.code, model='agent')
                sdb.commit()
                yield _sse('error', {
                    'ai_status': 'unavailable' if e.status == 503 else 'error',
                    'ai_error': {'code': e.code, 'message': e.message, 'hint': e.details.get('hint'), 'provider_status': e.details.get('provider_status')},
                })

    return StreamingResponse(event_stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no'})


@router.put('/sessions/{session_id}/messages/{message_id}/feedback', response_model=MessageOut)
def answer_feedback(session_id: uuid.UUID, message_id: uuid.UUID, body: AnswerFeedbackIn, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """The technician marks one AI answer as helpful or not, with an optional note on what was wrong. Stored on the message
    itself, so it stays with the conversation; the manager dashboard counts it. Sending helpful=null removes the rating."""
    s = get_owned_session(db, u, session_id)
    m = db.scalar(select(Conversation).where(Conversation.id == message_id, Conversation.session_id == s.id, Conversation.role == 'assistant'))
    if m is None:
        raise NotFound('Message not found.')
    meta = dict(m.meta or {})
    if body.helpful is None:
        meta.pop('feedback', None)
    else:
        note = (body.comment or '').strip() or None
        meta['feedback'] = {'helpful': body.helpful, 'comment': note, 'at': utcnow().isoformat()}
    m.meta = meta
    db.flush()
    return MessageOut.model_validate(m)


@router.get('/sessions/{session_id}/messages/{message_id}/speech')
async def message_speech(session_id: uuid.UUID, message_id: uuid.UUID, voice: str | None = Query(None, max_length=32), strict: bool = False,
                         u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """A stored assistant reply spoken in the technician's own ElevenLabs voice (MP3), or a Gemini voice (WAV). Requested by the app only for replies to voice messages
    while the speaker is on, or when the technician presses Read aloud. Errors carry a code so the app can fall back to the
    browser's own voice (MODEL_NOT_CONFIGURED, QUOTA_EXCEEDED...)."""
    from ...services import voice as voice_svc
    s = get_readable_session(db, u, session_id)
    m = db.scalar(select(Conversation).where(Conversation.id == message_id, Conversation.session_id == s.id, Conversation.role == 'assistant'))
    if m is None:
        raise NotFound('Message not found.')
    if voice != 'device':
        check_ai_quota(u.id)
    data, media_type, v = await voice_svc.speak(m, voice, strict=strict)
    return Response(data, media_type=media_type, headers={'Cache-Control': 'private, max-age=86400', 'X-Voice': v, 'X-Voice-Provider': voice_svc.provider_of(v)})


@router.get('/voice/status')
def voice_status(u: User = Depends(current_user)):
    """What the running backend loaded for speech. Never the key itself; its fingerprint only in development."""
    import hashlib
    from ...config import get_settings
    from ...integrations import elevenlabs
    s = get_settings(); k = s.elevenlabs_api_key or ''
    return {'preferred': 'elevenlabs' if elevenlabs.configured() else ('gemini' if s.gemini_tts_model else 'device'), 'strict': s.voice_strict,
            'elevenlabs': {'configured': elevenlabs.configured(), 'key_loaded': bool(k), 'voice_id': s.elevenlabs_voice_id, 'model': s.elevenlabs_model,
                           'model_kannada': s.elevenlabs_model_kannada or s.elevenlabs_model, 'output_format': elevenlabs.OUTPUT_FORMAT, 'voice_settings': elevenlabs.VOICE_SETTINGS,
                           **({'key_fingerprint': hashlib.sha256(k.encode()).hexdigest()[:10]} if k and s.app_env != 'production' else {}),
                           'paused_for_s': max(0, int(elevenlabs._BLOCKED_UNTIL['t'] - __import__('time').time()))},
            'gemini_tts': {'configured': bool(s.gemini_tts_model), 'model': s.gemini_tts_model, 'voice': s.gemini_tts_voice}}


VOICE_TEST_TEXT = 'Hello, this is FixSaathi speaking in your own voice. Switch off the MCB and confirm with your tester before you open anything.'


@router.post('/voice/test-personal')
async def test_personal_voice(u: User = Depends(current_user)):
    """Settings > Test my cloned voice: one fixed English sentence through ElevenLabs only. No fallback to Gemini or the device
    voice, so a failure is shown as it is. Costs about 130 ElevenLabs characters per press."""
    from ...integrations import elevenlabs
    from ...services import voice as voice_svc
    from ...config import get_settings
    if not elevenlabs.configured():
        raise AppError('ElevenLabs is not configured on the server (ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID).', code='MODEL_NOT_CONFIGURED', status=503)
    check_ai_quota(u.id)
    elevenlabs._BLOCKED_UNTIL['t'] = 0  # an explicit test always asks ElevenLabs again
    try:
        audio = await elevenlabs.synthesize(VOICE_TEST_TEXT, 'english')
    except AppError as e:
        voice_svc.log(voice_svc.logger, 'speech_provider', voice_svc.logging.WARNING, provider='none', wanted='elevenlabs', error=e.code, test=True)
        raise
    s = get_settings()
    voice_svc.log(voice_svc.logger, 'speech_provider', provider='elevenlabs', voice_id=s.elevenlabs_voice_id, model=s.elevenlabs_model, test=True, bytes=len(audio))
    return Response(audio, media_type=elevenlabs.MEDIA_TYPE, headers={'Cache-Control': 'no-store', 'X-Voice': 'personal', 'X-Voice-Provider': 'elevenlabs',
                                                                    'X-Voice-Model': s.elevenlabs_model, 'X-Voice-Id': s.elevenlabs_voice_id or ''})


async def _store_upload(db: Session, u: User, session_id: uuid.UUID, file: UploadFile, source: str, images_only: bool) -> MediaOut:
    from ...config import get_settings
    from ...integrations.storage.files import process_image, process_upload, safe_name
    from ...integrations.storage.local import InvalidUpload
    st = get_settings()
    s = get_owned_session(db, u, session_id); ensure_open(s)
    count = db.scalar(select(func.count()).select_from(Media).where(Media.session_id == s.id, Media.kind != 'generated')) or 0
    if count >= st.max_files_per_session:
        raise InvalidUpload(f'This session already has {count} files. Start a new session for more.', code='TOO_MANY_FILES', status=409)
    limit = max(st.max_upload_size_mb, st.max_document_size_mb) * 1024 * 1024
    data = await file.read(limit + 1)
    if images_only:
        p = process_image(data)
    else:
        p = process_upload(data, file.filename)
    if p.kind == 'image' and source == 'document':
        source = 'upload'
    kind = 'document' if p.kind == 'document' else source
    meta = dict(p.meta)
    if p.kind == 'image':
        meta.setdefault('filename', safe_name(file.filename, 'camera-photo.jpg' if source == 'capture' else 'photo'))
    key = get_storage().put(p.data, p.ext, f'sessions/{s.id}')
    m = Media(session_id=s.id, uploaded_by=u.id, kind=kind, storage_key=key, mime_type=p.mime, size_bytes=len(p.data), width=p.width, height=p.height, meta=meta)
    db.add(m); db.flush()
    return media_out(m)


@router.post('/sessions/{session_id}/images', response_model=MediaOut, status_code=201)
async def upload(session_id: uuid.UUID, file: UploadFile = File(...), source: str = Query('upload', pattern='^(upload|capture)$'),
                 u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """Images only (kept for older clients). Photos are re-encoded without EXIF/GPS metadata."""
    return await _store_upload(db, u, session_id, file, source, images_only=True)


@router.post('/sessions/{session_id}/files', response_model=MediaOut, status_code=201)
async def upload_file(session_id: uuid.UUID, file: UploadFile = File(...), source: str = Query('upload', pattern='^(upload|capture)$'),
                      u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    """Images, PDFs, Word (.docx) and text files. Validated by content; see integrations/storage/files.py."""
    return await _store_upload(db, u, session_id, file, source, images_only=False)


@router.get('/sessions/{session_id}/images', response_model=list[MediaOut])
def list_images(session_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    s = get_readable_session(db, u, session_id)
    return [media_out(m) for m in db.scalars(select(Media).where(Media.session_id == s.id).order_by(Media.created_at))]


@router.get('/media/{media_id}')
def get_media(media_id: uuid.UUID, u: User = Depends(current_user), db: Session = Depends(get_db, scope="function")):
    m = db.get(Media, media_id)
    if not m:
        raise NotFound('File not found.')
    s = get_readable_session(db, u, m.session_id)  # authorisation through the owning session
    headers = {'Cache-Control': 'private, max-age=300', 'X-Content-Type-Options': 'nosniff'}
    if m.kind == 'document':
        from urllib.parse import quote
        name = (m.meta or {}).get('filename') or f'document.{m.storage_key.rsplit(".", 1)[-1]}'
        inline = m.mime_type in ('application/pdf', 'text/plain', 'text/csv', 'text/markdown')
        headers['Content-Disposition'] = f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(name)}"
        headers['Content-Security-Policy'] = "default-src 'none'; sandbox"  # nothing in a document can run scripts
    media_type = f'{m.mime_type}; charset=utf-8' if m.mime_type.startswith('text/') else m.mime_type
    try:
        data = get_storage().get(m.storage_key)
    except AppError as e:
        if e.code == 'MEDIA_MISSING' and m.kind != 'generated' and (m.meta or {}).get('demo'):
            from ...demo.scenarios import HERE, SCENARIOS
            sc = SCENARIOS.get(is_demo(s) or '')
            photo = sc and sc.get('photo')
            if photo and (HERE / photo).is_file():
                return Response((HERE / photo).read_bytes(), media_type=media_type, headers=headers)
        raise
    return Response(data, media_type=media_type, headers=headers)
