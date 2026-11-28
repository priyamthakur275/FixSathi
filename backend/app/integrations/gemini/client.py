"""Central Gemini access. Every model call in the backend goes through this module.
- Credentials and model IDs come only from configuration.
- No silent model substitution: if a model ID is not configured the call raises AIUnavailable.
  Fallbacks happen only through GEMINI_AGENT_FALLBACK_MODELS, which the operator sets explicitly; every switch is logged.
"""
import asyncio, json, logging, random, time
from typing import Any, TypeVar
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError
from ...config import get_settings
from ...core.exceptions import AIError, AIUnavailable, AppError
from ...core.logging import log
from .errors import classify

logger = logging.getLogger('gemini')
T = TypeVar('T', bound=BaseModel)
LAST_STATUS: dict = {'ok': None}
# Models that just answered quota / billing / not-found are skipped for a while, so every message doesn't wait on them again.
COOLDOWN: dict[str, float] = {}
CONSECUTIVE_FAILURES: dict[str, int] = {}
CIRCUIT_BREAKER_THRESHOLD = 2
CIRCUIT_BREAKER_SECONDS = 300.0  # 5 minutes after 2 consecutive timeouts or 429s
CIRCUIT_BREAKER_CODES = frozenset({'QUOTA_EXCEEDED', 'BILLING_REQUIRED', 'AI_TIMEOUT', 'PROVIDER_UNAVAILABLE'})
MODELS_CHECK_CACHE: dict[str, Any] = {'at': 0.0, 'models': []}
# A model that is not found stays unavailable (retired or not in the key's tier), so it is skipped for hours, not minutes.
COOL_CODES = {'QUOTA_EXCEEDED': 60.0, 'BILLING_REQUIRED': CIRCUIT_BREAKER_SECONDS, 'MODEL_NOT_FOUND': 6 * 3600.0, 'PROVIDER_UNAVAILABLE': 60.0, 'AI_TIMEOUT': 60.0}
# Models that rejected the full JSON schema (SCHEMA_UNSUPPORTED): later calls send the relaxed schema at once instead of
# spending a failed call first. Live log 21 Nov: every diagnosis on gemini-3.1-flash-lite cost two calls.
RELAXED_SCHEMA: set[str] = set()
QUOTA_RETRY_MAX_WAIT = 20.0  # a quota that resets later than this (e.g. a daily limit) is not retried: the retry cannot succeed
# Errors after which the next configured model is tried instead of failing the request.
FAILOVER_CODES = ('QUOTA_EXCEEDED', 'BILLING_REQUIRED', 'MODEL_NOT_FOUND', 'SCHEMA_UNSUPPORTED', 'PROVIDER_UNAVAILABLE', 'AI_TIMEOUT', 'NETWORK_ERROR')
# Free-text chat only: when the agent model has not answered after this many seconds, the first fallback is asked as well and
# whichever answers first is used. Live log 21 Nov: the same prompt took 11 s to 60 s on Google's side, and a single slow
# attempt plus its retry kept "Writing the answer" on screen for 90 s. JSON outputs (diagnosis, guidance) are never hedged.
HEDGED_OPS = ('chat',)
# Streaming chat only: the first two models get one retry after a 503 or timeout, with 400-800 ms jitter, before moving on.
STREAM_RETRY_CODES = frozenset({'PROVIDER_UNAVAILABLE', 'AI_TIMEOUT'})
STREAM_RETRY_JITTER = (0.4, 0.8)
STREAM_RETRY_MODELS = 2
# Models with no quota on the current key (live 27 Nov: gemini-4-neon always 429) are skipped for 5 minutes after a 429,
# so their rate-limit message no longer replaces the real error from the other models.
SKIP_AFTER_429_MODELS = frozenset({'gemini-4-neon'})
SKIP_AFTER_429_SECONDS = 300.0
QUOTA_CODES = frozenset({'QUOTA_EXCEEDED', 'BILLING_REQUIRED'})
LAST_429: dict[str, float] = {}
GEMINI_BUSY_MESSAGE = "Google's Gemini service is busy right now. Please press Retry in a few seconds."
TEXT_OUTPUT_CAP = {'chat': 2048, 'challenger': 650}  # output tokens, thinking included
MODEL_SETTINGS = {'agent': 'gemini_agent_model', 'live': 'gemini_live_model', 'embed': 'gemini_embed_model', 'image': 'nano_banana_model', 'tts': 'gemini_tts_model'}
# Prebuilt Gemini TTS voices offered in Settings: each was generated and measured (21-22 Nov; docs/VOICE.md).
TTS_VOICES = ('Charon', 'Leda', 'Achird', 'Sulafat', 'Puck', 'Kore', 'Iapetus', 'Orus', 'Alnilam', 'Sadaltager')
TTS_SAMPLE_RATE = 24000  # the TTS models return 16-bit mono PCM at 24 kHz ("audio/L16;codec=pcm;rate=24000")
# Gemini TTS is steered by a natural-language direction before the transcript; the direction itself is not spoken.
# services/voice.direction() builds one per reply (tone and language); this is the default when none is given.
TTS_STYLE = ('Read the following aloud as a confident, experienced appliance repair expert guiding a technician: clear, crisp and warm, '
             'at a natural brisk pace, with natural emphasis on the key actions and short pauses between steps.')


_SCHEMA_LIMITS = {'maxLength', 'minLength', 'maxItems', 'minItems', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum'}


def _relax_schema(x: Any) -> Any:
    """The same JSON schema without length/count/range limits (structure, types and enums are kept)."""
    if isinstance(x, dict):
        return {k: _relax_schema(v) for k, v in x.items() if k not in _SCHEMA_LIMITS}
    if isinstance(x, list):
        return [_relax_schema(v) for v in x]
    return x


class CallResult(BaseModel):
    model: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None


class GeminiClient:
    def __init__(self, client: Any | None = None):
        self._client = client
        self._injected = client is not None
        self._beta: Any | None = None

    @property
    def configured(self) -> bool:
        return self._client is not None or get_settings().ai_configured

    def model(self, kind: str) -> str:
        s = get_settings()
        m = getattr(s, MODEL_SETTINGS[kind])
        if not self.configured:
            raise AIUnavailable('Gemini is not configured on the server (GEMINI_API_KEY is missing).')
        if not m:
            raise AIUnavailable(f'No model configured for {kind}. Set {MODEL_SETTINGS[kind].upper()}.', code='MODEL_NOT_CONFIGURED')
        return m

    @property
    def raw(self) -> Any:
        if self._client is None:
            s = get_settings()
            if not s.ai_configured:
                raise AIUnavailable('Gemini is not configured on the server (GEMINI_API_KEY is missing).')
            opts = types.HttpOptions(timeout=int(s.gemini_timeout_seconds * 1000))
            if s.google_genai_use_vertexai:
                self._client = genai.Client(vertexai=True, project=s.google_cloud_project, location=s.google_cloud_region, http_options=opts)
            else:
                self._client = genai.Client(api_key=s.gemini_api_key, http_options=opts)
        return self._client

    @property
    def raw_beta(self) -> Any:
        """Client for the v1beta API. The TTS models' speech_config exists only there: on v1 the request fails with
        'Unknown name "speechConfig"' (checked 21 Nov), which is why spoken replies previously looked unavailable."""
        if self._injected:
            return self._client
        if self._beta is None:
            s = get_settings()
            if s.google_genai_use_vertexai:
                return self.raw
            if not s.ai_configured:
                raise AIUnavailable('Gemini is not configured on the server (GEMINI_API_KEY is missing).')
            self._beta = genai.Client(api_key=s.gemini_api_key, http_options=types.HttpOptions(api_version='v1beta', timeout=int(s.gemini_timeout_seconds * 1000)))
        return self._beta

    async def speech(self, text: str, voice: str, direction: str | None = None) -> tuple[bytes, CallResult]:
        """Speaks text with a prebuilt Gemini voice. Returns 16-bit mono PCM at TTS_SAMPLE_RATE. While the model is cooling down
        (e.g. the free tier's daily TTS limit) this raises at once instead of spending another request."""
        model = self.model('tts')
        if voice not in TTS_VOICES:
            raise AppError(f'Unknown voice "{voice}".', code='VOICE_NOT_SUPPORTED', details={'voices': list(TTS_VOICES)})
        until = COOLDOWN.get(model, 0)
        if until > time.time():
            raise AIUnavailable('The natural voice has reached its limit for now.', code='QUOTA_EXCEEDED', details={'model': model, 'retry_after_s': int(until - time.time())})
        cfg = types.GenerateContentConfig(response_modalities=['AUDIO'], speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))))
        # The preview TTS model now and then answers STOP with no audio part (22 Nov: once in production, once locally; the
        # identical request then succeeded). One retry covers it; a second empty answer lets the app use the device voice.
        for attempt in range(2):
            resp, meta = await self._call('tts', model, lambda: self.raw_beta.aio.models.generate_content(model=model, contents=f'{direction or TTS_STYLE}\n\n{text}', config=cfg))
            cands = getattr(resp, 'candidates', None) or []
            for c in cands:
                for p in (getattr(getattr(c, 'content', None), 'parts', None) or []):
                    d = getattr(p, 'inline_data', None)
                    if d is not None and (d.mime_type or '').startswith('audio') and d.data:
                        return d.data, meta
            log(logger, 'tts_empty_audio', logging.WARNING, model=model, attempt=attempt, finish=str(getattr(cands[0], 'finish_reason', None)) if cands else 'NO_CANDIDATES')
        raise AIError('The voice model returned no audio.', code='AI_EMPTY', details={'op': 'tts'})

    @staticmethod
    def _op_timeout(op: str) -> float:
        s = get_settings()
        if op == 'chat':
            return float(s.gemini_chat_timeout_seconds)
        if op == 'challenger':
            return float(s.gemini_challenger_timeout_seconds)
        if op in ('diagnosis', 'guidance', 'nameplate', 'part_locator'):
            return float(s.gemini_diagnosis_timeout_seconds)
        return float(s.gemini_timeout_seconds)

    @staticmethod
    def _record_success(model: str) -> None:
        CONSECUTIVE_FAILURES.pop(model, None)
        COOLDOWN.pop(model, None)

    @staticmethod
    def _record_failure(model: str, code: str, retry_after: float | None) -> None:
        if code in CIRCUIT_BREAKER_CODES or code == 'MODEL_NOT_FOUND':
            n = CONSECUTIVE_FAILURES.get(model, 0) + 1
            CONSECUTIVE_FAILURES[model] = n
            base = COOL_CODES.get(code, 60.0)
            if code in CIRCUIT_BREAKER_CODES and n >= CIRCUIT_BREAKER_THRESHOLD:
                base = max(base, CIRCUIT_BREAKER_SECONDS)
            wait_s = max(retry_after or 0.0, base)
            COOLDOWN[model] = time.time() + min(wait_s, max(3600.0, base))

    async def _call(self, op: str, model: str, fn, last_resort: bool = True):
        """Bounded retries with jittered backoff, only for transient categories. Never retries bad keys, permissions or unknown models.
        With last_resort=False a quota, overload or timeout error is raised at once, so the caller moves to a fallback model instead of waiting."""
        s = get_settings()
        timeout_s = self._op_timeout(op)
        for attempt in range(s.gemini_max_retries + 1):
            t0 = time.perf_counter()
            try:
                resp = await asyncio.wait_for(fn(), timeout=timeout_s)
                ms = int((time.perf_counter() - t0) * 1000)
                um = getattr(resp, 'usage_metadata', None)
                meta = CallResult(model=model, latency_ms=ms, input_tokens=getattr(um, 'prompt_token_count', None), output_tokens=getattr(um, 'candidates_token_count', None))
                log(logger, 'gemini_call', op=op, model=model, ms=ms, attempt=attempt, input_tokens=meta.input_tokens, output_tokens=meta.output_tokens)
                LAST_STATUS.update(ok=True, op=op, model=model, code=None, at=time.time())
                self._record_success(model)
                return resp, meta
            except Exception as e:  # noqa: BLE001 - every failure is classified below
                c = classify(e, model)
                log(logger, 'gemini_call_failed', logging.WARNING, op=op, model=model, attempt=attempt, error_code=c.code, provider_http=c.provider_http,
                    provider_status=c.provider_status, provider_message=c.provider_message, ms=int((time.perf_counter() - t0) * 1000))
                LAST_STATUS.update(ok=False, op=op, model=model, code=c.code, hint=c.hint, at=time.time())
                self._record_failure(model, c.code, c.retry_after)
                if c.code in QUOTA_CODES:
                    LAST_429[model] = time.time()
                if c.code in FAILOVER_CODES and not last_resort:
                    pass  # fall through to raise: a fallback model is available
                elif c.code == 'QUOTA_EXCEEDED' and (c.retry_after or 0) > QUOTA_RETRY_MAX_WAIT:
                    pass  # e.g. "retry in 58084s" on a free-tier daily limit
                elif c.retryable and attempt < s.gemini_max_retries:
                    jitter = random.uniform(0.05, 0.35)
                    base_wait = c.retry_after if c.retry_after is not None else 0.35 * (2 ** attempt)
                    await asyncio.sleep(min(base_wait + jitter, 4.0)); continue
                err_cls = AIUnavailable if c.http_status == 503 else AIError
                raise err_cls(c.message, code=c.code, status=c.http_status, details=c.details(model)) from e

    @staticmethod
    def _text_or_raise(resp, op: str) -> str:
        fb = getattr(resp, 'prompt_feedback', None)
        if fb is not None and getattr(fb, 'block_reason', None):
            raise AIError('Gemini declined to answer this request. Rephrase it and try again.', code='AI_BLOCKED', details={'reason': str(fb.block_reason)})
        cands = getattr(resp, 'candidates', None) or []
        text = (getattr(resp, 'text', None) or '').strip() if cands else ''
        if not text:
            reason = str(getattr(cands[0], 'finish_reason', '')) if cands else 'NO_CANDIDATES'
            if 'SAFETY' in reason or 'PROHIBITED' in reason:
                raise AIError('Gemini declined to answer this request. Rephrase it and try again.', code='AI_BLOCKED', details={'reason': reason})
            raise AIError('The AI model returned an empty response.', code='AI_EMPTY', details={'reason': reason, 'op': op})
        return text

    def _agent_models(self, op: str | None = None) -> list[str]:
        s = get_settings()
        extra = [m.strip() for m in (s.gemini_agent_fallback_models or '').split(',') if m.strip()]
        first = self.model('agent')
        ordered = [first] + [m for m in extra if m != first]
        if op == 'chat' and s.gemini_fast_model:
            fast = s.gemini_fast_model
            return [fast] + [m for m in ordered if m != fast]
        return ordered

    def _cfg(self, **kw) -> types.GenerateContentConfig:
        lvl = (get_settings().gemini_thinking_level or '').strip().lower()
        if lvl and not getattr(self, '_no_thinking_cfg', False):
            kw['thinking_config'] = types.ThinkingConfig(thinking_level=lvl)
        return types.GenerateContentConfig(**kw)

    async def _agent_call(self, op: str, contents: Any, **cfg_kw):
        """Try the agent model, then each configured fallback, on rate-limit/tier/overload/timeout errors. Each switch is logged."""
        configured = self._agent_models(op)
        now = time.time()
        ready = [m for m in configured if COOLDOWN.get(m, 0) <= now]
        cooling = sorted((m for m in configured if m not in ready), key=lambda m: COOLDOWN[m])
        models = ready + cooling  # cooling models stay as a last resort
        skipped = [m for m in models if m in SKIP_AFTER_429_MODELS and now - LAST_429.get(m, 0.0) < SKIP_AFTER_429_SECONDS]
        if skipped and len(skipped) < len(models):
            models = [m for m in models if m not in skipped]
            log(logger, 'gemini_models_skipped_recent_429', op=op, models=skipped)
        if cooling:
            log(logger, 'gemini_models_cooling', op=op, skipped=cooling)
        hedge = get_settings().gemini_hedge_seconds if op in HEDGED_OPS else 0
        if hedge <= 0 or len(models) < 2:
            return await self._try_models(op, models, configured, contents, cfg_kw)
        first = asyncio.create_task(self._try_models(op, models[:1], configured, contents, cfg_kw, final=False))
        done, _ = await asyncio.wait({first}, timeout=hedge)
        if done:
            e = first.exception()
            if e is None:
                return first.result()
            if getattr(e, 'code', None) not in FAILOVER_CODES:
                raise e
            return await self._try_models(op, models[1:], configured, contents, cfg_kw)
        log(logger, 'gemini_hedge_started', logging.WARNING, op=op, slow=models[0], backup=models[1], after_s=hedge)
        pending = {first, asyncio.create_task(self._try_models(op, models[1:], configured, contents, cfg_kw))}
        last: BaseException | None = None
        try:
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for t in done:
                    if t.exception() is None:
                        return t.result()
                    last = t.exception()
            raise last  # type: ignore[misc]
        finally:
            for t in pending:
                t.cancel()  # the slower request is abandoned; its result would be discarded anyway

    async def _try_models(self, op: str, models: list[str], configured: list[str], contents: Any, cfg_kw: dict, final: bool = True):
        """Each model in turn. Only the last model of the final group waits on quota or retries an overload."""
        last: Exception | None = None
        for i, model in enumerate(models):
            lr = final and i == len(models) - 1
            kw = cfg_kw
            if model in RELAXED_SCHEMA and 'response_json_schema' in cfg_kw:
                kw = {**cfg_kw, 'response_json_schema': _relax_schema(cfg_kw['response_json_schema'])}
            try:
                try:
                    resp, meta = await self._call(op, model, lambda: self.raw.aio.models.generate_content(model=model, contents=contents, config=self._cfg(**kw)),
                                                  last_resort=lr)
                except AIError as e:
                    if e.code == 'SCHEMA_UNSUPPORTED' and 'response_json_schema' in cfg_kw and model not in RELAXED_SCHEMA:
                        # Smaller models reject large constrained schemas. Retry this model once with the length/count limits
                        # removed; generate_json still validates the reply against the full Pydantic schema.
                        log(logger, 'schema_relaxed', logging.WARNING, op=op, model=model)
                        RELAXED_SCHEMA.add(model)
                        relaxed = {**cfg_kw, 'response_json_schema': _relax_schema(cfg_kw['response_json_schema'])}
                        resp, meta = await self._call(op, model, lambda: self.raw.aio.models.generate_content(model=model, contents=contents, config=self._cfg(**relaxed)),
                                                      last_resort=lr)
                    elif e.code == 'INVALID_REQUEST' and (get_settings().gemini_thinking_level or '').strip() and not getattr(self, '_no_thinking_cfg', False):
                        self._no_thinking_cfg = True  # this model does not accept thinking_level; stop sending it
                        log(logger, 'thinking_config_disabled', logging.WARNING, model=model)
                        resp, meta = await self._call(op, model, lambda: self.raw.aio.models.generate_content(model=model, contents=contents, config=self._cfg(**cfg_kw)))
                    else:
                        raise
                if model != configured[0]:
                    log(logger, 'gemini_fallback_used', logging.WARNING, op=op, primary=configured[0], used=model)
                return resp, meta
            except (AIUnavailable, AIError) as e:
                last = e
                if e.code in FAILOVER_CODES and i < len(models) - 1:
                    continue
                raise
        raise last  # pragma: no cover

    async def generate_json(self, op: str, schema: type[T], contents: Any, system: str, temperature: float = 0.2) -> tuple[T, CallResult]:
        cap = TEXT_OUTPUT_CAP.get(op)
        resp, meta = await self._agent_call(op, contents, system_instruction=system, temperature=temperature, response_mime_type='application/json',
                                            response_json_schema=schema.model_json_schema(), **({'max_output_tokens': cap} if cap else {}))
        text = self._text_or_raise(resp, op)
        try:
            return schema.model_validate(json.loads(text)), meta
        except (json.JSONDecodeError, ValidationError) as e:
            log(logger, 'gemini_invalid_json', logging.WARNING, op=op, model=meta.model)
            raise AIError('The AI model returned a response that failed validation.', code='AI_INVALID_OUTPUT') from e

    async def generate_text(self, op: str, contents: Any, system: str, temperature: float = 0.4) -> tuple[str, CallResult]:
        cap = TEXT_OUTPUT_CAP.get(op)  # bounds cost and latency of free-text replies; JSON outputs are not capped (truncation breaks them)
        resp, meta = await self._agent_call(op, contents, system_instruction=system, temperature=temperature, **({'max_output_tokens': cap} if cap else {}))
        return self._text_or_raise(resp, op), meta

    async def stream_text(self, op: str, contents: Any, system: str, temperature: float = 0.4):
        """Stream text chunks from Gemini, failing over between configured models only before the first chunk."""
        configured = self._agent_models(op)
        now = time.time()
        ready = [m for m in configured if COOLDOWN.get(m, 0) <= now]
        cooling = sorted((m for m in configured if m not in ready), key=lambda m: COOLDOWN[m])
        models = ready + cooling
        skipped = [m for m in models if m in SKIP_AFTER_429_MODELS and now - LAST_429.get(m, 0.0) < SKIP_AFTER_429_SECONDS]
        if skipped and len(skipped) < len(models):
            models = [m for m in models if m not in skipped]
            log(logger, 'gemini_models_skipped_recent_429', op=op, models=skipped)
        cap = TEXT_OUTPUT_CAP.get(op)
        kw = dict(system_instruction=system, temperature=temperature, **({'max_output_tokens': cap} if cap else {}))
        timeout_s = self._op_timeout(op)
        last: Exception | None = None
        failures: list[tuple[str, str]] = []
        for i, model in enumerate(models):
            attempts = 2 if i < STREAM_RETRY_MODELS else 1
            for attempt in range(attempts):
                t0 = time.perf_counter()
                sent_any = False
                in_tok = out_tok = None
                try:
                    stream = await asyncio.wait_for(
                        self.raw.aio.models.generate_content_stream(model=model, contents=contents, config=self._cfg(**kw)),
                        timeout=timeout_s,
                    )
                    async for chunk in stream:
                        um = getattr(chunk, 'usage_metadata', None)
                        if um is not None:
                            in_tok = getattr(um, 'prompt_token_count', in_tok)
                            out_tok = getattr(um, 'candidates_token_count', out_tok)
                        txt = getattr(chunk, 'text', None) or ''
                        if txt:
                            sent_any = True
                            yield txt, None
                    if not sent_any:
                        raise AIError('The AI model returned an empty response.', code='AI_EMPTY', details={'op': op})
                    ms = int((time.perf_counter() - t0) * 1000)
                    meta = CallResult(model=model, latency_ms=ms, input_tokens=in_tok, output_tokens=out_tok)
                    log(logger, 'gemini_call', op=op, model=model, ms=ms, attempt=attempt, stream=True, input_tokens=in_tok, output_tokens=out_tok)
                    LAST_STATUS.update(ok=True, op=op, model=model, code=None, at=time.time())
                    self._record_success(model)
                    if model != configured[0]:
                        log(logger, 'gemini_fallback_used', logging.WARNING, op=op, primary=configured[0], used=model)
                    yield '', meta
                    return
                except Exception as e:  # noqa: BLE001
                    if isinstance(e, AIError) and e.code == 'AI_EMPTY' and i == len(models) - 1:
                        raise
                    c = classify(e, model)
                    log(logger, 'gemini_call_failed', logging.WARNING, op=op, model=model, error_code=c.code, stream=True, attempt=attempt,
                        provider_http=c.provider_http, provider_status=c.provider_status, provider_message=c.provider_message,
                        ms=int((time.perf_counter() - t0) * 1000))
                    LAST_STATUS.update(ok=False, op=op, model=model, code=c.code, hint=c.hint, at=time.time())
                    self._record_failure(model, c.code, c.retry_after)
                    if c.code in QUOTA_CODES:
                        LAST_429[model] = time.time()
                    err_cls = AIUnavailable if c.http_status == 503 else AIError
                    last = err_cls(c.message, code=c.code, status=c.http_status, details=c.details(model))
                    if sent_any:
                        raise last from e
                    failures.append((model, c.code))
                    if c.code in STREAM_RETRY_CODES and attempt + 1 < attempts:
                        await asyncio.sleep(random.uniform(*STREAM_RETRY_JITTER))
                        continue
                    if c.code in FAILOVER_CODES and i < len(models) - 1:
                        break  # next model
                    # A known no-quota model's 429 does not count: the real cause is what the other models answered.
                    relevant = [code for m, code in failures if not (m in SKIP_AFTER_429_MODELS and code in QUOTA_CODES)]
                    if relevant and all(code == 'PROVIDER_UNAVAILABLE' for code in relevant):
                        raise AIUnavailable(GEMINI_BUSY_MESSAGE, code='PROVIDER_UNAVAILABLE', status=503, details=c.details(model)) from e
                    raise last from e
        if last:  # pragma: no cover
            raise last

    async def generate_image(self, prompt: str, reference: tuple[bytes, str] | None = None) -> tuple[bytes, str, CallResult]:
        model = self.model('image')
        parts: list[Any] = [prompt]
        if reference:
            parts.append(types.Part.from_bytes(data=reference[0], mime_type=reference[1]))
        cfg = types.GenerateContentConfig(response_modalities=['IMAGE', 'TEXT'])
        resp, meta = await self._call('image_generation', model, lambda: self.raw.aio.models.generate_content(model=model, contents=parts, config=cfg))
        for c in getattr(resp, 'candidates', None) or []:
            for p in getattr(getattr(c, 'content', None), 'parts', None) or []:
                inline = getattr(p, 'inline_data', None)
                if inline and inline.data and (inline.mime_type or '').startswith('image/'):
                    return inline.data, inline.mime_type, meta
        raise AIError('The image model did not return an image.', code='AI_NO_IMAGE')

    async def embed(self, texts: list[str], task: str = 'RETRIEVAL_DOCUMENT') -> tuple[list[list[float]], str]:
        model = self.model('embed')
        cfg = types.EmbedContentConfig(task_type=task)
        resp, _ = await self._call('embed', model, lambda: self.raw.aio.models.embed_content(model=model, contents=texts, config=cfg))
        vecs = [list(e.values or []) for e in (resp.embeddings or [])]
        if len(vecs) != len(texts) or any(not v for v in vecs):
            raise AIError('The embedding model returned an incomplete response.', code='AI_INVALID_OUTPUT')
        return vecs, model


_singleton: GeminiClient | None = None


def get_gemini() -> GeminiClient:
    global _singleton
    if _singleton is None:
        _singleton = GeminiClient()
    return _singleton


def get_cached_models_available() -> list[str]:
    return list(MODELS_CHECK_CACHE.get('models') or [])


async def probe_available_models(force: bool = False) -> list[str]:
    """Cheap cached startup self-check listing which configured models are visible/callable (names only, no keys)."""
    now = time.time()
    if not force and MODELS_CHECK_CACHE.get('at') and now - float(MODELS_CHECK_CACHE['at']) < 300.0:
        return get_cached_models_available()
    s = get_settings()
    if not s.ai_configured:
        MODELS_CHECK_CACHE.update(at=now, models=[])
        return []
    candidates = [m for m in dict.fromkeys([
        s.gemini_fast_model or '',
        s.gemini_agent_model or '',
        *[x.strip() for x in (s.gemini_agent_fallback_models or '').split(',') if x.strip()],
        s.gemini_embed_model or '',
        s.gemini_live_model or '',
        s.gemini_tts_model or '',
        s.nano_banana_model or '',
    ]) if m]
    g = get_gemini()
    visible: set[str] = set()
    try:
        async for m in await asyncio.wait_for(g.raw.aio.models.list(config={'page_size': 200}), timeout=5.0):
            visible.add((m.name or '').removeprefix('models/'))
        async for m in await asyncio.wait_for(g.raw_beta.aio.models.list(config={'page_size': 200}), timeout=5.0):
            visible.add((m.name or '').removeprefix('models/'))
    except Exception as e:  # noqa: BLE001
        log(logger, 'startup_models_check_failed', logging.WARNING, error=classify(e).code)
        return get_cached_models_available()
    found = [m for m in candidates if m in visible]
    MODELS_CHECK_CACHE.update(at=now, models=found)
    log(logger, 'startup_models_check', models=found)
    return found


def set_gemini(c: GeminiClient | None) -> None:
    """Used by tests to inject a fake client."""
    global _singleton
    _singleton = c
