"""Deterministic fakes shared by unit tests and the browser end-to-end server. No network."""
import io
from PIL import Image
from app.integrations.gemini import client as gclient


def png(size=(64, 48), fmt='PNG') -> bytes:
    b = io.BytesIO(); Image.new('RGB', size, (120, 30, 30)).save(b, fmt); return b.getvalue()


class FakeGemini(gclient.GeminiClient):
    """Deterministic stand-in. Scripted outputs; no network."""
    def __init__(self):
        super().__init__(client=object())
        self.json: dict = {}; self.text = 'Demo-free scripted reply'; self.fail: dict = {}; self.calls: list = []; self.systems: list = []

    def model(self, kind):
        return {'agent': 'fake-agent', 'live': 'fake-live', 'embed': 'fake-embed', 'image': 'fake-image', 'tts': 'fake-tts'}[kind]

    async def generate_json(self, op, schema, contents, system, temperature=0.2):
        self.calls.append((op, contents))
        if op in self.fail: raise self.fail[op]
        import json
        from pydantic import ValidationError
        from app.core.exceptions import AIError
        try:
            return schema.model_validate(json.loads(self.json[op]) if isinstance(self.json[op], str) else self.json[op]), gclient.CallResult(model='fake-agent', latency_ms=5)
        except (ValidationError, ValueError) as e:
            raise AIError('The AI model returned a response that failed validation.', code='AI_INVALID_OUTPUT') from e

    async def generate_text(self, op, contents, system, temperature=0.4):
        self.calls.append((op, contents)); self.systems.append(system)
        if op in self.fail: raise self.fail[op]
        return self.text, gclient.CallResult(model='fake-agent', latency_ms=5)

    async def speech(self, text, voice, direction=None):
        self.calls.append(('tts', text, voice, direction))
        if 'tts' in self.fail: raise self.fail['tts']
        return b'\x00\x01' * 2400, gclient.CallResult(model='fake-tts', latency_ms=5)

    async def generate_image(self, prompt, reference=None):
        return png(), 'image/png', gclient.CallResult(model='fake-image', latency_ms=5)

    async def embed(self, texts, task='RETRIEVAL_DOCUMENT'):
        words = ['fan', 'capacitor', 'ac', 'cooling', 'drum', 'noise', 'slow', 'hum']
        return [[float(w in t.lower()) + 0.01 for w in words] for t in texts], 'fake-embed'


DIAG = {'appliance_type': 'ceiling_fan', 'problem_summary': 'Fan slow with hum', 'possible_faults': [
    {'fault': 'Worn bearings', 'explanation': 'x', 'confidence': 0.2, 'evidence': [{'source': 'technician_statement', 'detail': 'hums'}]},
    {'fault': 'Weak capacitor', 'explanation': 'y', 'confidence': 0.6, 'evidence': [{'source': 'observed_in_image', 'detail': 'bulging capacitor'}]}],
    'recommended_checks': ['spin by hand'], 'follow_up_questions': ['Does speed change?'], 'safety_requirements': ['Isolate power'], 'requires_escalation': False}
STEPS = {'steps': [{'title': 'Observe', 'instruction': 'Watch the fan', 'kind': 'observation', 'requires_power_off': False},
                   {'title': 'Open canopy', 'instruction': 'Remove canopy', 'kind': 'power_sensitive', 'requires_power_off': False}]}


