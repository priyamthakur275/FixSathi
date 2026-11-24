# Live WebSocket protocol: `/api/v1/live/{session_id}`

The browser connects to FastAPI. FastAPI connects to Gemini Live with `client.aio.live.connect(model=GEMINI_LIVE_MODEL, config=...)`. The API key never leaves the server. Origins must be in `CORS_ORIGINS` (others are closed with 4403).

## Client → server
| type | fields | notes |
|---|---|---|
| `auth` | `token`, `language?` | **Must be first**, within 10 s. The token is never placed in the URL (so it stays out of access logs). |
| `audio_chunk` | `data` base64 | 16-bit mono PCM, 16 kHz, ≤ 64 KB per chunk. Sent as `send_realtime_input(audio=Blob(mime_type='audio/pcm;rate=16000'))`. |
| `audio_stream_end` | | sent on mute |
| `video_frame` | `data` base64 JPEG | ≤ 400 KB. Throttled to `LIVE_VIDEO_FPS` and dropped under back-pressure. |
| `text_input` | `text` | for noisy sites |
| `end_session` | | |

## Server → client
`session_ready{model}`, `transcription{role,text}`, `assistant_text{text}`, `audio_chunk{mime_type,data}` (24 kHz PCM), `interrupted` (stop playback: barge-in), `turn_complete`, `tool_call_status{name,status}`, `diagnosis{...}`, `part_located{url,box,...}`, `step{...}`, `safety_blocked{allowed:false,reason,missing,disclaimer}`, `safety_confirmation_required{missing}`, `escalated`, `notice{GO_AWAY}`, `error{code,message,fatal}`, `session_ended`.

## Tools the model can call (executed by the server)
`get_diagnosis`, `locate_part` (uses the latest frame; stores that one frame), `give_step` (always via `SafetyService.guard`), `request_safety_confirmation` (cannot change safety state), `escalate_to_senior`.

## Limits and cleanup
- Inbound queue bounded at 64 items; video is dropped first.
- Idle timeout `LIVE_IDLE_TIMEOUT_SECONDS`.
- On disconnect or error, all tasks are cancelled and the Gemini session is closed. Transcripts are saved at every `turn_complete` and on close.
- Raw audio and video are not stored.
- Not implemented yet: session resumption across reconnects.
