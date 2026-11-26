"""Translate every failure from the google-genai SDK into one clear, safe category.
Provider messages are passed through (trimmed and scrubbed) because they say exactly what is wrong; they never contain the API key."""
import asyncio, re
from dataclasses import dataclass
import httpx
from google.genai import errors
try:  # google-genai 3.x sends requests through httpx2, whose exceptions do not subclass httpx's
    import httpx2
    _HTTPX2_TIMEOUT: tuple = (httpx2.TimeoutException,)
    _HTTPX2_ERROR: tuple = (httpx2.HTTPError,)
except ImportError:  # pragma: no cover - older SDKs use httpx only
    _HTTPX2_TIMEOUT = _HTTPX2_ERROR = ()

# Classic Google API keys (AIza...), newer bound keys (AQ....) and key= query parameters.
KEYLIKE = re.compile(r'AIza[0-9A-Za-z_\-]{20,}|AQ\.[0-9A-Za-z_\-.]{20,}|key=[^&\s]+')


@dataclass
class Classified:
    code: str
    http_status: int      # what FixSaathi returns to its own client
    message: str          # safe for end users
    hint: str             # what the operator should do
    retryable: bool
    provider_http: int | None = None
    provider_status: str | None = None
    provider_message: str | None = None
    retry_after: float | None = None   # seconds Google asked us to wait (429 RetryInfo)

    def details(self, model: str | None) -> dict:
        return {'model': model, 'provider_http_status': self.provider_http, 'provider_status': self.provider_status,
                'provider_message': self.provider_message, 'hint': self.hint}


def _configured_key() -> str | None:
    try:
        from ...config import get_settings
        return get_settings().gemini_api_key
    except BaseException:  # noqa: BLE001 - settings may be unavailable (e.g. in isolated unit tests)
        return None


def scrub(s: str | None, n: int = 300) -> str | None:
    if not s:
        return s
    key = _configured_key()
    if key and len(key) >= 8:  # whatever its format, the configured key itself never leaves the server
        s = s.replace(key, '[redacted]')
    return KEYLIKE.sub('[redacted]', s)[:n]


def classify(e: BaseException, model: str | None = None) -> Classified:
    if isinstance(e, errors.APIError):
        code, status, msg = e.code, (e.status or ''), scrub(e.message or '') or ''
        low = f'{msg} {e.details}'.lower()
        base = dict(provider_http=code, provider_status=status or None, provider_message=msg or None)
        if 'api key not valid' in low or 'api_key_invalid' in low or 'api key expired' in low:
            return Classified('INVALID_API_KEY', 503, 'The server\'s Gemini API key is invalid, expired or revoked.',
                              'Create a new key in Google AI Studio, put it in GEMINI_API_KEY in backend/.env (no quotes or spaces), restart the backend.', False, **base)
        if 'location is not supported' in low:
            return Classified('REGION_NOT_SUPPORTED', 503, 'Gemini is not available from the server\'s location.', 'Run the backend from a supported region or use Vertex AI.', False, **base)
        if code == 401 or status == 'UNAUTHENTICATED':
            return Classified('UNAUTHORIZED', 503, 'Gemini did not accept the server\'s credentials.', 'Check GEMINI_API_KEY or the Vertex AI service account.', False, **base)
        if code == 403 or status == 'PERMISSION_DENIED':
            return Classified('PERMISSION_DENIED', 503, 'The Gemini API key is not allowed to use this model or API.',
                              'In Google Cloud, enable the Generative Language API for the key\'s project and remove key restrictions that block it.', False, **base)
        if code == 404 or status == 'NOT_FOUND':
            return Classified('MODEL_NOT_FOUND', 503, f'The model "{model}" is not available for this API key.',
                              'Run python scripts/check_gemini.py to list the models your key can use, then fix the model ID in backend/.env.', False, **base)
        if code == 429 or status == 'RESOURCE_EXHAUSTED':
            m = re.search(r'retry[^0-9]{0,40}?(\d+(?:\.\d+)?)s', f'{msg} {e.details}', re.I)
            wait = float(m.group(1)) if m else None
            # "limit: 0" means this model is not included in the key's tier at all. Any other free-tier 429 is a normal
            # per-minute/per-day rate limit: transient, so retry (or move to the configured fallback model).
            if re.search(r'limit:\s*0\b', low) or ('billing' in low and 'free' not in low):
                return Classified('BILLING_REQUIRED', 503, 'This model is not included in the API key\'s tier.',
                                  'Attach billing (or your Buildathon credits) to the key\'s project, or set a model your tier allows.', False, retry_after=wait, **base)
            return Classified('QUOTA_EXCEEDED', 503, 'Gemini is rate-limiting this API key right now. Please try again in a few seconds.',
                              'Free-tier keys allow only a few requests per minute. Set GEMINI_AGENT_FALLBACK_MODELS in backend/.env, or enable billing.', True, retry_after=wait, **base)
        if status == 'FAILED_PRECONDITION' and 'billing' in low:
            return Classified('BILLING_REQUIRED', 503, 'Billing must be enabled for this Gemini request.', 'Attach billing to the key\'s project.', False, **base)
        if (code == 400 or status == 'INVALID_ARGUMENT') and ('too many states' in low or 'schema' in low and 'constraint' in low):
            # Some smaller models cannot serve large response schemas. Model-specific: the next fallback model may accept it.
            return Classified('SCHEMA_UNSUPPORTED', 502, f'The model "{model}" cannot produce this structured response.',
                              'Use a larger model for GEMINI_AGENT_MODEL, or keep a fallback model that supports the schema.', False, **base)
        if code == 400 or status == 'INVALID_ARGUMENT':
            return Classified('INVALID_REQUEST', 502, 'Gemini rejected the request format.', 'This is an application bug or an unsupported model feature; see provider_message in the logs.', False, **base)
        if code and code >= 500:
            return Classified('PROVIDER_UNAVAILABLE', 503, 'Gemini is temporarily unavailable. Try again shortly.', 'Transient Google error; retried automatically.', True, **base)
        return Classified('AI_ERROR', 502, 'The AI service returned an unexpected error.', 'See provider_message in the logs.', False, **base)
    ws_status = getattr(getattr(e, 'response', None), 'status_code', None)  # Live API WebSocket handshake rejected
    if isinstance(ws_status, int):
        base = dict(provider_http=ws_status, provider_message=type(e).__name__)
        if ws_status == 404:
            return Classified('LIVE_NOT_AVAILABLE', 503, f'Live voice is not available for this API key (model "{model}").',
                              'This key cannot open Gemini Live sessions. Use a key/tier with Live API access, or use the browser voice mode.', False, **base)
        if ws_status in (401, 403):
            return Classified('PERMISSION_DENIED', 503, 'The Gemini API key is not allowed to open Live sessions.', 'Check the key\'s Live API access.', False, **base)
        if ws_status == 429:
            return Classified('QUOTA_EXCEEDED', 503, 'Gemini is rate-limiting this API key right now. Please try again in a few seconds.', 'Live API quota reached.', True, **base)
    if isinstance(e, (asyncio.TimeoutError, httpx.TimeoutException, *_HTTPX2_TIMEOUT)):
        return Classified('AI_TIMEOUT', 504, 'The AI model took too long to respond.', 'Retry; if it persists raise GEMINI_TIMEOUT_SECONDS.', True)
    if isinstance(e, (httpx.HTTPError, OSError, *_HTTPX2_ERROR)):
        return Classified('NETWORK_ERROR', 503, 'The server cannot reach Google\'s AI service.', 'Check the backend machine\'s internet, proxy or firewall (generativelanguage.googleapis.com:443).', True,
                          provider_message=type(e).__name__)
    return Classified('AI_INTERNAL_ERROR', 500, 'Something went wrong while calling the AI.', f'Unexpected {type(e).__name__}; see backend logs.', False,
                      provider_message=type(e).__name__)
