import asyncio, logging, os, sys, time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from .api.v1.router import api
from .config import get_settings
from .core.exceptions import install_handlers
from .core.logging import RequestIdMiddleware, log, setup_logging
from .core.security_headers import SecurityHeadersMiddleware
from .db.session import SessionLocal

logger = logging.getLogger('app')


@asynccontextmanager
async def lifespan(_: FastAPI):
    s = get_settings()  # fails fast with a clear error if SECRET_KEY or DATABASE_URL is missing
    setup_logging(s.debug)
    log(logger, 'startup', env=s.app_env, ai_configured=s.ai_configured, storage=s.storage_provider, vector_mode=s.vector_search_mode)
    try:
        from .services.knowledge_base import seed_curated
        with SessionLocal() as db:
            n = seed_curated(db)
            db.commit()
        log(logger, 'knowledge_seeded', added=n)
    except Exception as e:
        log(logger, 'knowledge_seed_skipped', logging.WARNING, error=type(e).__name__)
    if s.ai_configured and 'pytest' not in sys.modules:
        from .integrations.gemini.client import probe_available_models
        asyncio.create_task(probe_available_models())
    yield
    log(logger, 'shutdown')


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title='FixSaathi API', version='1.0.0', lifespan=lifespan, docs_url='/docs', redoc_url='/redoc')
    app.add_middleware(CORSMiddleware, allow_origins=s.cors_list, allow_credentials=False, allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
                       allow_headers=['Authorization', 'Content-Type', 'X-Request-ID'], expose_headers=['X-Request-ID', 'X-Voice', 'X-Voice-Provider', 'X-Voice-Model', 'X-Voice-Id'])  # X-Voice: which voice spoke (personal or a Gemini voice)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    install_handlers(app)
    app.include_router(api)

    @app.api_route('/health', methods=['GET', 'HEAD'], tags=['health'])
    def health():
        """For uptime monitors. 200 only when the database answers; 503 otherwise. AI status is reported, not required:
        without a key the app still runs (with AI_NOT_CONFIGURED errors and the labelled demo mode)."""
        from fastapi.responses import JSONResponse
        st = get_settings(); t0 = time.perf_counter()
        try:
            with SessionLocal() as db:
                db.execute(text('select 1'))
            db_ok = True
        except Exception:
            db_ok = False
        from .integrations.gemini.client import get_cached_models_available
        body = {'status': 'ok' if db_ok else 'unhealthy', 'env': st.app_env,
                'commit': (os.environ.get('RENDER_GIT_COMMIT') or '')[:7] or None,
                'database': 'ok' if db_ok else 'unreachable',
                'db_ms': int((time.perf_counter() - t0) * 1000), 'storage': st.storage_provider,
                'ai': {'configured': st.ai_configured,
                       'models': {'agent': bool(st.gemini_agent_model), 'live': bool(st.gemini_live_model), 'embed': bool(st.gemini_embed_model), 'image': bool(st.nano_banana_model)},
                       'models_available': get_cached_models_available()},
                'mode': 'ai' if st.ai_configured else 'no AI key set: AI endpoints return AI_NOT_CONFIGURED; demo scenarios still work'}
        return JSONResponse(body, status_code=200 if db_ok else 503, headers={'Cache-Control': 'no-store'})

    @app.get('/ready', tags=['health'])
    def ready():
        from fastapi.responses import JSONResponse
        try:
            with SessionLocal() as db:
                db.execute(text('select 1'))
            ok = True
        except Exception:
            ok = False
        return JSONResponse({'ready': ok, 'database': 'ok' if ok else 'unreachable'}, status_code=200 if ok else 503)

    if not _mount_frontend(app, s.frontend_dist):
        @app.get('/', tags=['health'])
        def root():
            return {
                'service': 'FixSaathi API',
                'status': 'ok',
                'version': '1.0.0',
                'api_prefix': '/api/v1',
                'health': '/health',
                'ready': '/ready',
                'docs': '/docs',
            }
    return app


def _mount_frontend(app: FastAPI, dist: str | None) -> bool:
    """Serve the built React app so the website and API share one origin (no CORS, WebSockets just work)."""
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    if not dist or not (Path(dist) / 'index.html').is_file():
        return False
    root = Path(dist).resolve()
    app.mount('/assets', StaticFiles(directory=root / 'assets'), name='assets')

    @app.api_route('/{path:path}', methods=['GET', 'HEAD'], include_in_schema=False)
    def spa(path: str):
        if path.startswith(('api/', 'docs', 'redoc', 'openapi.json', 'health', 'ready')):
            raise HTTPException(404)
        f = (root / path).resolve()
        if path and f.is_file() and root in f.parents:
            return FileResponse(f)
        return FileResponse(root / 'index.html', headers={'Cache-Control': 'no-cache'})
    return True


app = create_app()
