# FixSaathi frontend (prototype)

Voice-first AI repair copilot UI. React 19 + TypeScript + Vite + Tailwind 4 + React Router + Framer Motion + Recharts + Lucide.

## Run
    npm ci
    npm run dev        # http://localhost:5173
    npm run build      # type-check + production build into dist/

Camera works on localhost or HTTPS only (browser rule).

## Backend

All screens use the FastAPI backend through `src/services/index.ts` and `src/services/api.ts`. There are no mock services left.
Set `VITE_API_BASE_URL` (default `http://localhost:8000`). The access token is held in memory, and the refresh token in localStorage. No API keys are ever in the frontend.

- Voice: `src/hooks/useLiveVoice.ts` streams 16 kHz PCM (AudioWorklet `public/mic-worklet.js`) and 1 fps JPEG frames over `/api/v1/live/{id}`, and plays 24 kHz PCM replies.
- Safety checkboxes reflect server state. Locked steps come from the server with their instruction hidden.
