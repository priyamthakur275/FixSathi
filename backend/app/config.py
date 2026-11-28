from functools import lru_cache
from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or backend/.env). No secrets in code."""
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    app_env: str = 'development'
    debug: bool = False
    secret_key: str = Field(..., min_length=32, description='JWT signing key, at least 32 characters')
    database_url: str = Field(..., description='postgresql+psycopg://user:pass@host:5432/db')
    cors_origins: str = 'http://localhost:5173'
    frontend_dist: str | None = None  # when set, the API also serves the built website (single-service deploy)
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    gemini_api_key: str | None = None
    google_genai_use_vertexai: bool = False
    google_cloud_project: str | None = None
    google_cloud_region: str = 'asia-south1'
    gemini_live_model: str | None = None
    gemini_agent_model: str | None = None
    # Optional fast model used first for free-text chat replies (`op='chat'`); agent_model + fallbacks remain primary for diagnosis/vision.
    gemini_fast_model: str | None = None
    # Comma-separated models tried in order when the agent model is rate-limited or not in the key's tier. Logged on every use.
    gemini_agent_fallback_models: str | None = None
    # Lower thinking = much faster replies. low | medium | high | empty (model default).
    gemini_thinking_level: str | None = 'low'
    gemini_embed_model: str | None = None
    nano_banana_model: str | None = None
    gemini_timeout_seconds: float = 45
    gemini_chat_timeout_seconds: float = 8.0
    gemini_diagnosis_timeout_seconds: float = 20.0
    gemini_challenger_timeout_seconds: float = 5.0
    receipt_ttl_days: int = 30
    gemini_max_retries: int = 1
    # Chat replies only: seconds before the first fallback model is also asked (0 disables). See HEDGED_OPS in the Gemini client.
    gemini_hedge_seconds: float = 12
    # Spoken replies (Gemini text-to-speech). Empty: the app speaks with the browser's voice instead.
    gemini_tts_model: str | None = None
    # One of TTS_VOICES in the Gemini client. Charon: chosen 21 Nov from six measured samples (see docs/VOICE.md).
    gemini_tts_voice: str = 'Charon'
    # ElevenLabs (the technician's own cloned voice). Used first for spoken replies when key and voice id are set; Gemini TTS
    # and then the browser voice are the fallbacks. Gemini still writes every reply.
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None
    elevenlabs_model: str = 'eleven_multilingual_v2'
    elevenlabs_model_kannada: str | None = None   # empty: Kannada uses elevenlabs_model
    elevenlabs_timeout_seconds: float = 30
    # Diagnostics: true = the personal voice never falls back (no Gemini voice on the server, no device voice in the app);
    # the ElevenLabs error is shown instead. Keep false in production.
    voice_strict: bool = False

    storage_provider: str = 'local'
    local_storage_path: str = 'uploads'
    max_upload_size_mb: int = 8
    max_document_size_mb: int = 15  # PDFs, Word and text files
    max_files_per_session: int = 60

    alloydb_enabled: bool = False
    alloydb_database_url: str | None = None
    vector_search_mode: str = 'auto'  # auto | embeddings | keyword

    safety_confirmation_ttl_minutes: int = 60
    live_video_fps: float = 1.0
    live_max_frame_bytes: int = 400_000
    live_max_audio_chunk_bytes: int = 64_000
    live_idle_timeout_seconds: int = 300
    auth_rate_limit_per_minute: int = 10
    # Per technician account, for calls that spend the Gemini / ElevenLabs key (chat, diagnosis, steps, photos, voice). 0 = no limit.
    ai_requests_per_minute: int = 20
    ai_requests_per_day: int = 400

    @field_validator('gemini_api_key', 'gemini_live_model', 'gemini_agent_model', 'gemini_fast_model', 'gemini_embed_model', 'nano_banana_model', 'gemini_tts_model',
                     'elevenlabs_api_key', 'elevenlabs_voice_id', 'elevenlabs_model_kannada', mode='before')
    @classmethod
    def _strip(cls, v):
        # A key pasted with quotes, spaces or a newline is a common cause of 'API key not valid'.
        if v is None:
            return None
        v = str(v).strip().strip('"').strip("'").strip()
        return v or None

    @field_validator('database_url')
    @classmethod
    def _db(cls, v: str) -> str:
        v = v.strip()
        if v.startswith('postgres://'):
            v = 'postgresql+psycopg://' + v[len('postgres://'):]
        elif v.startswith('postgresql://'):
            v = 'postgresql+psycopg://' + v[len('postgresql://'):]
        if not v.startswith(('postgresql', 'sqlite')):
            raise ValueError('DATABASE_URL must be a PostgreSQL URL')
        return v

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(',') if o.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.gemini_api_key or (self.google_genai_use_vertexai and self.google_cloud_project))


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        missing = ', '.join(sorted({str(x['loc'][0]).upper() for x in e.errors()}))
        raise SystemExit(
            f'FixSaathi cannot start: check {missing} in backend/.env.\n'
            '  - First run? Create the file with:  python scripts/setup_env.py\n'
            '  - SECRET_KEY must be at least 32 characters; DATABASE_URL looks like postgresql+psycopg://user:pass@localhost:5432/fixsaathi'
        ) from None
