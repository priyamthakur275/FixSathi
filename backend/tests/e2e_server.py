"""Starts the real FastAPI app with a deterministic fake Gemini, for browser end-to-end tests only. Never used in production."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import uvicorn
from app.integrations.gemini import client as gclient
from app.services import live
from tests.fakes import DIAG, STEPS, FakeGemini

f = FakeGemini(); f.json = {'diagnosis': DIAG, 'guidance': STEPS, 'part_locator': {'found': True, 'component_name': 'Capacitor', 'explanation': 'Visible near the canopy (test fixture)', 'box': {'x_min': 250, 'y_min': 250, 'x_max': 650, 'y_max': 700}, 'confidence': 0.4}}
f.text = 'Test reply from the fake model used in end-to-end tests.'
if os.environ.get('E2E_FAIL_CHAT'):  # reproduce a real provider failure through the real classifier
    from google.genai import errors as gerr
    from app.integrations.gemini.client import GeminiClient
    class Failing(GeminiClient):
        def __init__(self): super().__init__(client=object())
        def model(self, kind): return 'gemini-3.6-flash'
        async def generate_text(self, op, contents, system, temperature=0.4):
            async def boom(): raise gerr.ClientError(400, {'error': {'code': 400, 'status': 'INVALID_ARGUMENT', 'message': 'API key not valid. Please pass a valid API key.', 'details': [{'reason': 'API_KEY_INVALID'}]}})
            return await self._call(op, 'gemini-3.6-flash', boom)
    f = Failing()
gclient.set_gemini(f)
os.environ.setdefault('GEMINI_EMBED_MODEL', '')
uvicorn.run('app.main:app', host='127.0.0.1', port=int(os.environ.get('PORT', 8000)))
