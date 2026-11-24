# Security notes

## Rotate any key that has been shown in a screenshot, chat or commit
1. Google AI Studio → API keys → create a new key, then **delete** the old one. Deleting is what actually revokes it.
2. Put the new key only in `backend/.env` (or the root `.env` for Docker), with no quotes and no spaces. Restart the backend.
3. Run `python scripts/check_gemini.py`.
4. If a key was ever committed to git, deleting the file is not enough: the key stays in history. Rotate it, then rewrite history (for example with `git filter-repo`) or treat the old key as public forever.
5. Rotate `SECRET_KEY` too if it was exposed. Doing so signs everyone out.

Never paste keys into chats, screenshots or issues.

## What the code does
- Secrets come only from the environment. `.env` is git-ignored and docker-ignored. The frontend has no secrets: `VITE_*` values are public by design.
- The Gemini key stays on the server. Live voice is relayed by the backend, and the browser authenticates with its own short-lived JWT, sent as the first WebSocket message rather than in the URL.
- Passwords use Argon2. Access tokens are HS256 JWTs (30 min). Refresh tokens are random, stored only as SHA-256 hashes, rotated on every use, and revocable on logout.
- Roles: technician, manager, admin. Organisation scoping is applied in `services/access.py` on every query. A forbidden session returns 404.
- Rate limits on login, register and refresh (per process).
- Uploads: decoded with Pillow (the declared MIME type is not trusted), JPEG/PNG/WebP only, 8 MB limit, stored under generated keys with path-traversal protection, and served only after a session-ownership check.
- SQL: ORM and bound parameters only. The full-text query is built from `[a-z0-9]` tokens.
- CORS: explicit origin list, no wildcard. The WebSocket checks Origin against the same list.
- Logs are JSON with request IDs. Fields named password, token, secret, api_key or authorization are redacted. Provider messages are scrubbed of anything key-like.

## Known gaps
- The rate limiter is per instance. Use Cloud Armor or Redis for multi-instance limits.
- Local file storage only. Add Cloud Storage with private buckets for Cloud Run.
- The refresh token lives in localStorage, which is a trade-off for a single-page app. Move it to an httpOnly cookie if the frontend and API share a domain.
