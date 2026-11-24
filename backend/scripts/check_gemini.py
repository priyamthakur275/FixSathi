"""Diagnose Gemini configuration on YOUR machine. Never prints the key.

    python scripts/check_gemini.py            # free: validates the key and model IDs via models.list (no tokens used)
    python scripts/check_gemini.py --call     # + one tiny text call and one tiny embedding call (costs a fraction of a cent)
    python scripts/check_gemini.py --call --image --live   # + one image generation and a Live connect/close (image generation costs more)
"""
import argparse, asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.config import get_settings
from app.integrations.gemini.client import GeminiClient
from app.integrations.gemini.errors import classify

NEED = {'agent': 'generateContent', 'image': 'generateContent', 'embed': 'embedContent', 'live': 'bidiGenerateContent'}


def show(label, ok, msg=''):
    print(f"  [{'OK ' if ok else 'FAIL'}] {label}{(': ' + msg) if msg else ''}")


async def main(a):
    s = get_settings(); g = GeminiClient()
    print('Configuration')
    show('GEMINI_API_KEY present', bool(s.gemini_api_key) or s.google_genai_use_vertexai, f'length {len(s.gemini_api_key or "")}, Vertex AI={s.google_genai_use_vertexai}')
    models = {'agent': s.gemini_agent_model, 'live': s.gemini_live_model, 'embed': s.gemini_embed_model, 'image': s.nano_banana_model}
    for k, v in models.items():
        show(f'{k} model set', bool(v), v or f'set {"GEMINI_" + k.upper() + "_MODEL" if k != "image" else "NANO_BANANA_MODEL"}')
    if not s.ai_configured:
        print('\nNo key configured. Add GEMINI_API_KEY to backend/.env and run again.'); return 1
    print('\nKey and model availability (models.list, free)')
    try:
        avail = {}
        async for m in await g.raw.aio.models.list(config={'page_size': 200}):
            avail[(m.name or '').removeprefix('models/')] = set(m.supported_actions or [])
        show('API key accepted by Google', True, f'{len(avail)} models visible')
    except Exception as e:  # noqa: BLE001
        c = classify(e); show('API key accepted by Google', False, f'{c.code}: {c.message}'); print(f'        Google said: {c.provider_message}\n        Fix: {c.hint}'); return 1
    bad = 0
    for k, v in models.items():
        if not v:
            continue
        if v not in avail:
            close = [n for n in avail if n.split('-')[0:2] == v.split('-')[0:2]][:6]
            show(f'{k}: {v}', False, f'not visible to this key. Similar: {", ".join(close) or "none"}'); bad += 1
        elif NEED[k] not in avail[v]:
            show(f'{k}: {v}', False, f'does not support {NEED[k]} (supports {", ".join(sorted(avail[v]))})'); bad += 1
        else:
            show(f'{k}: {v}', True, f'supports {NEED[k]}')
    if a.call:
        print('\nReal calls')
        for label, coro in [('text generation', g.generate_text('check', 'Reply with the single word OK.', 'Be brief.')), ('embedding', g.embed(['ceiling fan hums']))]:
            try:
                await coro; show(label, True)
            except Exception as e:  # noqa: BLE001
                d = getattr(e, 'details', {}) or {}; show(label, False, f"{getattr(e, 'code', type(e).__name__)}: {e}"); print(f"        Google said: {d.get('provider_message')}\n        Fix: {d.get('hint')}"); bad += 1
        if a.image:
            try:
                data, mime, _ = await g.generate_image('A simple flat illustration of a ceiling fan capacitor, labelled.'); show('image generation', True, f'{mime}, {len(data)} bytes')
            except Exception as e:  # noqa: BLE001
                d = getattr(e, 'details', {}) or {}; show('image generation', False, f"{getattr(e, 'code', '')}: {e}"); print(f"        Google said: {d.get('provider_message')}"); bad += 1
        if a.live:
            from app.services.live import build_config
            try:
                async with g.raw.aio.live.connect(model=s.gemini_live_model, config=build_config('English')):
                    pass
                show('Live connect', True)
            except Exception as e:  # noqa: BLE001
                c = classify(e, s.gemini_live_model); show('Live connect', False, f'{c.code}: {c.provider_message or c.message}'); bad += 1
    print('\nAll checks passed.' if not bad else f'\n{bad} problem(s) found.')
    return 1 if bad else 0

p = argparse.ArgumentParser(); p.add_argument('--call', action='store_true'); p.add_argument('--image', action='store_true'); p.add_argument('--live', action='store_true')
sys.exit(asyncio.run(main(p.parse_args())))
