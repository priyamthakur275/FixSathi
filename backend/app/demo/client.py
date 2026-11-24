"""Stand-in for the Gemini client in labelled demo sessions only. Returns the scenario's scripted content.
The model name 'demo-scenario' is stored with every output so the UI labels it as a demo, never as AI."""
import io, json
from PIL import Image, ImageDraw
from ..integrations.gemini.client import CallResult, GeminiClient
from .scenarios import DEMO_MODEL, SCENARIOS


class DemoClient(GeminiClient):
    def __init__(self, scenario: str, turn: int = 0):
        super().__init__(client=object()); self.sc = SCENARIOS[scenario]; self.turn = turn

    @property
    def configured(self) -> bool: return True

    def model(self, kind: str) -> str: return DEMO_MODEL

    def _meta(self) -> CallResult: return CallResult(model=DEMO_MODEL, latency_ms=0)

    async def generate_text(self, op, contents, system, temperature=0.4):
        replies = self.sc['chat']; return replies[min(self.turn, len(replies) - 1)], self._meta()

    async def generate_json(self, op, schema, contents, system, temperature=0.2):
        return schema.model_validate(json.loads(json.dumps(self.sc[op]))), self._meta()

    async def generate_image(self, prompt, reference=None):
        im = Image.new('RGB', (768, 432), (14, 32, 58)); d = ImageDraw.Draw(im)
        d.rectangle([24, 24, 744, 408], outline=(47, 196, 176), width=3)
        d.text((48, 190), 'Demo scenario: no AI picture is generated in demo mode.', fill=(230, 240, 250))
        b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue(), 'image/png', self._meta()

    async def embed(self, texts, task='RETRIEVAL_DOCUMENT'):
        from ..core.exceptions import AIUnavailable
        raise AIUnavailable('Embeddings are not used in demo mode.', code='DEMO_NO_EMBEDDINGS')


def is_demo(s) -> str | None:
    d = getattr(s, 'appliance_details', None) or {}
    sc = d.get('demo_scenario')
    return sc if sc in SCENARIOS else None
