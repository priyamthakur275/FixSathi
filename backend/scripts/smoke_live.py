"""Live Gemini end-to-end smoke check (NO MOCKS).

Verifies against a real Gemini API key (in backend/.env or environment, never committed):
  (a) A real SSE streamed chat reply arrives via POST /api/v1/sessions/{id}/messages/stream
  (b) Gemini Vision reads a nameplate/error image via POST /api/v1/sessions/{id}/read-nameplate
  (c) A power-sensitive repair step is withheld while the safety lock is locked, and appears
      after both isolation statements ("power_off_confirmed", "tester_checked") are recorded.

Usage (from backend/ or repo root):
  python scripts/smoke_live.py
  python scripts/smoke_live.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_IMAGE = REPO_ROOT / 'docs' / 'samples' / 'sample_nameplate.png'

sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)  # Ensures pydantic-settings loads backend/.env if present


def _step(label: str, ok: bool, detail: str = '') -> None:
    tag = 'OK  ' if ok else 'FAIL'
    print(f'  [{tag}] {label}{(": " + detail) if detail else ""}')


def _skip(label: str, detail: str = '') -> None:
    print(f'  [SKIP] {label}{(": " + detail) if detail else ""}')


def _parse_sse(raw_lines: list[str]) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    cur_event = 'message'
    data_buf: list[str] = []
    for line in raw_lines:
        if line.startswith('event:'):
            cur_event = line.split(':', 1)[1].strip()
        elif line.startswith('data:'):
            data_buf.append(line.split(':', 1)[1].strip())
        elif line == '' and data_buf:
            payload = json.loads('\n'.join(data_buf))
            events.append((cur_event, payload))
            cur_event = 'message'
            data_buf = []
    if data_buf:
        events.append((cur_event, json.loads('\n'.join(data_buf))))
    return events


async def _stream_chat(client, headers: dict, session_id: str, prompt: str) -> tuple[list[str], dict]:
    deltas: list[str] = []
    done_payload: dict | None = None
    error_payload: dict | None = None
    async with client.stream(
        'POST',
        f'/api/v1/sessions/{session_id}/messages/stream',
        json={'text': prompt, 'media_ids': [], 'channel': 'text'},
        headers=headers,
        timeout=90.0,
    ) as resp:
        if resp.status_code != 200:
            body = (await resp.aread()).decode('utf-8', errors='replace')
            raise RuntimeError(f'Stream HTTP {resp.status_code}: {body}')
        cur_event = 'message'
        data_buf: list[str] = []
        async for line in resp.aiter_lines():
            if line.startswith('event:'):
                cur_event = line.split(':', 1)[1].strip()
            elif line.startswith('data:'):
                data_buf.append(line.split(':', 1)[1].strip())
            elif line == '' and data_buf:
                payload = json.loads('\n'.join(data_buf))
                if cur_event == 'delta':
                    deltas.append(payload.get('text', ''))
                elif cur_event == 'done':
                    done_payload = payload
                elif cur_event == 'error':
                    error_payload = payload
                cur_event = 'message'
                data_buf = []
    if error_payload is not None:
        err = error_payload.get('ai_error') or {}
        raise RuntimeError(f"Stream AI error [{err.get('code')}]: {err.get('message')}")
    if done_payload is None:
        raise RuntimeError('SSE stream finished without a done event')
    return deltas, done_payload


async def run_smoke(base_url: str | None, image_path: Path) -> int:
    import httpx
    from app.config import get_settings
    from app.services.safety import WITHHELD_MARK

    if not image_path.exists():
        _step('Sample nameplate image exists', False, f'missing {image_path}')
        return 1
    _step('Sample nameplate image exists', True, str(image_path))

    if base_url:
        client_cm = httpx.AsyncClient(base_url=base_url.rstrip('/'), timeout=90.0)
    else:
        settings = get_settings()
        if not settings.ai_configured:
            _step(
                'Gemini configuration (GEMINI_API_KEY / Vertex)',
                False,
                'not configured (set GEMINI_API_KEY in backend/.env or environment; never committed)',
            )
            return 1
        _step(
            'Gemini configuration (GEMINI_API_KEY / Vertex)',
            True,
            f'agent={settings.gemini_agent_model} (key length {len(settings.gemini_api_key or "")})',
        )
        from app.main import create_app
        app = create_app()
        client_cm = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://smoke.local', timeout=90.0)

    failures = 0
    async with client_cm as client:
        r = await client.get('/health')
        if r.status_code != 200:
            _step('GET /health', False, f'HTTP {r.status_code}')
            return 1
        h = r.json()
        ai_cfg = bool((h.get('ai') or {}).get('configured'))
        _step('GET /health', ai_cfg, f"ai.configured={ai_cfg}, model={(h.get('ai') or {}).get('agent_model')}")
        if not ai_cfg:
            print('        Cannot run live Gemini smoke check without GEMINI_API_KEY.')
            return 1

        # Create short-lived technician session and verify login + public evaluation endpoint
        uid = uuid.uuid4().hex[:10]
        email = f'smoke+{uid}@example.com'
        password = f'SmokePass-{uid}!'
        reg = await client.post(
            '/api/v1/auth/register',
            json={
                'full_name': 'Smoke Technician',
                'email': email,
                'password': password,
                'preferred_language': 'English',
            },
        )
        if reg.status_code != 201:
            _step('Register smoke technician', False, f'HTTP {reg.status_code}: {reg.text[:200]}')
            return 1
        _step('Register smoke technician', True)

        login_res = await client.post('/api/v1/auth/login', json={'email': email, 'password': password})
        if login_res.status_code != 200:
            _step('Login via POST /api/v1/auth/login', False, f'HTTP {login_res.status_code}: {login_res.text[:200]}')
            return 1
        token = login_res.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        _step('Login via POST /api/v1/auth/login', True)

        eval_res = await client.get('/api/v1/evaluation')
        eval_json = eval_res.json() if eval_res.status_code == 200 else {}
        eval_ok = eval_res.status_code == 200 and bool(eval_json.get('held_out') or eval_json.get('safety'))
        _step('Public GET /api/v1/evaluation', eval_ok, f'HTTP {eval_res.status_code}')
        if not eval_ok:
            failures += 1

        sess = await client.post(
            '/api/v1/sessions',
            json={'appliance_type': 'ceiling_fan', 'issue_description': 'Ceiling fan hums and runs slow'},
            headers=headers,
        )
        if sess.status_code != 201:
            _step('Create repair session', False, f'HTTP {sess.status_code}: {sess.text[:200]}')
            return 1
        sid = sess.json()['id']
        _step('Create repair session', True, sid)

        np_sid = None
        try:
            # (a) Real streamed chat reply (and verify locked safety withholding on capacitor step)
            locked_prompt = (
                'My ceiling fan hums and runs slow. Give numbered repair steps to remove the canopy cover, '
                'disconnect the capacitor wiring, and measure capacitor capacitance with a multimeter.'
            )
            deltas, done = await _stream_chat(client, headers, sid, locked_prompt)
            streamed_text = ''.join(deltas)
            msg = done.get('assistant_message') or {}
            saved_text = msg.get('message', '')
            withheld_count = (msg.get('meta') or {}).get('safety_withheld', 0)
            used_model = (msg.get('meta') or {}).get('model')
            stream_ok = bool(deltas) and bool(saved_text) and streamed_text == saved_text
            _step('(a) SSE streamed reply arrived (locked session)', stream_ok, f'{len(deltas)} deltas, {len(saved_text)} chars, model={used_model}')
            if not stream_ok:
                failures += 1

            locked_enforced = withheld_count > 0 or WITHHELD_MARK in streamed_text
            _step(
                '(c1) Power-sensitive step withheld while locked',
                locked_enforced,
                f'safety_withheld={withheld_count}, mark_present={WITHHELD_MARK in streamed_text}',
            )
            if not locked_enforced:
                print('        Warning: model reply did not trigger WITHHELD_MARK; excerpt:')
                print('       ', streamed_text[:280].replace('\n', ' '))
                failures += 1

            # (b) Gemini Vision nameplate & error display extraction on a split AC session
            np_sess = await client.post(
                '/api/v1/sessions',
                json={'appliance_type': 'unknown', 'issue_description': 'Split AC not cooling, reading nameplate and LED code'},
                headers=headers,
            )
            if np_sess.status_code != 201:
                _step('(b) Create nameplate session', False, f'HTTP {np_sess.status_code}: {np_sess.text[:200]}')
                failures += 1
            else:
                np_sid = np_sess.json()['id']
                with open(image_path, 'rb') as fh:
                    up = await client.post(
                        f'/api/v1/sessions/{np_sid}/files?source=capture',
                        files={'file': (image_path.name, fh.read(), 'image/png')},
                        headers=headers,
                    )
                if up.status_code != 201:
                    _step('(b) Upload nameplate image', False, f'HTTP {up.status_code}: {up.text[:200]}')
                    failures += 1
                else:
                    mid = up.json()['id']
                    np_res = await client.post(
                        f'/api/v1/sessions/{np_sid}/read-nameplate',
                        json={'media_id': mid},
                        headers=headers,
                        timeout=90.0,
                    )
                    if np_res.status_code != 200:
                        _step('(b) Gemini Vision read-nameplate', False, f'HTTP {np_res.status_code}: {np_res.text[:200]}')
                        failures += 1
                    else:
                        np_data = np_res.json()
                        ex = np_data.get('extracted') or {}
                        ret = np_data.get('retrieval') or {}
                        ok_np = np_data.get('status') == 'ok' and bool(ex.get('brand') or ex.get('model') or ex.get('error_code'))
                        _step(
                            '(b) Gemini Vision read-nameplate',
                            ok_np,
                            f"status={np_data.get('status')} brand={ex.get('brand')} model={ex.get('model')} error_code={ex.get('error_code')} hits={len(ret.get('hits') or [])} ai_model={ex.get('model_identifier')}",
                        )
                        if not ok_np:
                            print('        ai_error:', np_data.get('ai_error'))
                            failures += 1

            # (b2) Structured diagnosis showing real answering model
            diag_res = await client.post(f'/api/v1/sessions/{sid}/diagnose', json={}, headers=headers, timeout=90.0)
            if diag_res.status_code == 201:
                d_json = diag_res.json()
                _step('(b2) Structured diagnosis', True, f"model={d_json.get('model_identifier')} latency_ms={d_json.get('latency_ms')} faults={len(d_json.get('faults') or [])}")
            else:
                _step('(b2) Structured diagnosis', False, f'HTTP {diag_res.status_code}: {diag_res.text[:160]}')
                failures += 1

            # (c2) Record both technician safety statements -> confirm power-sensitive steps appear via stream
            conf = await client.post(
                f'/api/v1/sessions/{sid}/safety/confirm',
                json={'power_off_confirmed': True, 'tester_checked': True},
                headers=headers,
            )
            conf_ok = conf.status_code == 200 and bool(conf.json().get('unlocked'))
            _step('Record both safety statements (MCB off + tester)', conf_ok)
            if not conf_ok:
                failures += 1

            unlocked_prompt = (
                'Power is isolated at the MCB and verified with my tester. Now give the numbered repair steps '
                'to remove the ceiling fan canopy cover, disconnect the capacitor leads, test it, and fit a new one.'
            )
            deltas2, done2 = await _stream_chat(client, headers, sid, unlocked_prompt)
            streamed2 = ''.join(deltas2)
            msg2 = done2.get('assistant_message') or {}
            saved2 = msg2.get('message', '')
            withheld2 = (msg2.get('meta') or {}).get('safety_withheld', 0)
            used_model2 = (msg2.get('meta') or {}).get('model')
            unlocked_ok = bool(deltas2) and bool(saved2) and streamed2 == saved2 and withheld2 == 0 and WITHHELD_MARK not in streamed2
            _step(
                '(c2) Power-sensitive steps stream when unlocked',
                unlocked_ok,
                f'{len(deltas2)} deltas, safety_withheld={withheld2}, {len(saved2)} chars, model={used_model2}',
            )
            if not unlocked_ok:
                failures += 1
            # (d) Public sample nameplate endpoint check
            samp = await client.get('/api/v1/samples/nameplate')
            samp_ok = samp.status_code == 200 and samp.headers.get('content-type', '').startswith('image/png') and samp.content.startswith(b'\x89PNG')
            _step('GET /api/v1/samples/nameplate', samp_ok, f'HTTP {samp.status_code}, {len(samp.content)} bytes')
            if not samp_ok:
                failures += 1

            # (e) Hindi (Devanagari) & Hinglish language matching check
            hi_uid = uuid.uuid4().hex[:8]
            hi_reg = await client.post(
                '/api/v1/auth/register',
                json={'full_name': 'Hindi Smoke', 'email': f'smoke+hi+{hi_uid}@example.com', 'password': f'SmokePass-{hi_uid}!', 'preferred_language': 'Hindi'},
            )
            if hi_reg.status_code != 201:
                _step('(e) Hindi smoke registration', False, f'HTTP {hi_reg.status_code}')
                failures += 1
            else:
                hi_hdr = {'Authorization': f"Bearer {hi_reg.json()['access_token']}"}
                hi_sess = await client.post('/api/v1/sessions', json={'appliance_type': 'split_ac', 'issue_description': 'एसी ठंडा नहीं कर रहा CH38'}, headers=hi_hdr)
                if hi_sess.status_code != 201:
                    _step('(e) Hindi session create', False, f'HTTP {hi_sess.status_code}')
                    failures += 1
                else:
                    hi_sid = hi_sess.json()['id']
                    try:
                        d_hi, dn_hi = await _stream_chat(client, hi_hdr, hi_sid, 'एसी ठंडा नहीं कर रहा, इनडोर यूनिट में CH38 दिख रहा है, पहले क्या चेक करूँ?')
                        txt_hi = ''.join(d_hi)
                        has_devanagari = any('\u0900' <= ch <= '\u097f' for ch in txt_hi)
                        hi_ok = bool(txt_hi) and has_devanagari
                        _step('(e1) Devanagari Hindi reply', hi_ok, f'{len(txt_hi)} chars, devanagari={has_devanagari}, model={(dn_hi.get("assistant_message") or {}).get("meta", {}).get("model")}')
                        if not hi_ok:
                            print('        Hindi reply excerpt:', txt_hi[:200])
                            failures += 1

                        d_hg, dn_hg = await _stream_chat(client, hi_hdr, hi_sid, 'Ceiling fan slow chal raha hai aur humming aa rahi hai, bina khole kya check karun?')
                        txt_hg = ''.join(d_hg)
                        hg_ok = bool(txt_hg)
                        _step('(e2) Hinglish reply', hg_ok, f'{len(txt_hg)} chars, model={(dn_hg.get("assistant_message") or {}).get("meta", {}).get("model")}')
                        if not hg_ok:
                            failures += 1
                    finally:
                        await client.delete(f'/api/v1/sessions/{hi_sid}', headers=hi_hdr)

            # (f1) Optional Gemini TTS check (skipped if key lacks access or quota)
            msg2_id = msg2.get('id')
            if msg2_id:
                try:
                    tts_res = await client.get(f'/api/v1/sessions/{sid}/messages/{msg2_id}/speech', headers=headers, timeout=45.0)
                    if tts_res.status_code == 200 and tts_res.headers.get('content-type', '').startswith('audio/'):
                        _step('(f1) Optional Gemini TTS', True, f"HTTP 200, {tts_res.headers.get('content-type')}, {len(tts_res.content)} bytes")
                    elif tts_res.status_code in (403, 404, 429, 503):
                        _skip('(f1) Optional Gemini TTS', f'HTTP {tts_res.status_code} (key/quota/provider unavailable)')
                    else:
                        _skip('(f1) Optional Gemini TTS', f'HTTP {tts_res.status_code}: {tts_res.text[:100]}')
                except Exception as exc:
                    _skip('(f1) Optional Gemini TTS', f'{type(exc).__name__}: {exc}')

            # (f2) Optional Gemini Live WebSocket check (when --base-url is given)
            if base_url:
                try:
                    import websockets  # type: ignore
                    ws_url = base_url.rstrip('/').replace('https://', 'wss://').replace('http://', 'ws://') + f'/api/v1/live/{sid}'
                    async with websockets.connect(ws_url, open_timeout=15) as ws:
                        await ws.send(json.dumps({'type': 'auth', 'token': token, 'language': 'English'}))
                        live_model = None
                        got_reply = False
                        for _ in range(12):
                            ev = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                            et = ev.get('type')
                            if et == 'session_ready':
                                live_model = ev.get('model')
                                await ws.send(json.dumps({'type': 'text_input', 'text': 'Say hello in three words.'}))
                            elif et in ('transcription', 'audio_chunk'):
                                got_reply = True
                                await ws.send(json.dumps({'type': 'end_session'}))
                                break
                            elif et == 'error':
                                _skip('(f2) Optional Gemini Live WS', f"{ev.get('code')}: {ev.get('message')}")
                                break
                        if got_reply:
                            _step('(f2) Optional Gemini Live WS', True, f'model={live_model}, received live transcription/audio')
                        elif live_model and not got_reply:
                            _skip('(f2) Optional Gemini Live WS', f'connected ({live_model}) but no turn event before loop end')
                except Exception as exc:
                    _skip('(f2) Optional Gemini Live WS', f'{type(exc).__name__}: {exc}')
        finally:
            await client.delete(f'/api/v1/sessions/{sid}', headers=headers)
            if np_sid:
                await client.delete(f'/api/v1/sessions/{np_sid}', headers=headers)

    print('\nSmoke result:', 'ALL PASSED' if failures == 0 else f'{failures} CHECK(S) FAILED')
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Run unmocked live Gemini smoke verification.')
    parser.add_argument('--base-url', default=None, help='Optional running backend URL (default: in-process ASGI app)')
    parser.add_argument('--image', default=str(DEFAULT_IMAGE), help='Sample nameplate/error image path')
    args = parser.parse_args()
    return asyncio.run(run_smoke(args.base_url, Path(args.image)))


if __name__ == '__main__':
    raise SystemExit(main())
