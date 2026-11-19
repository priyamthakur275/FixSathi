# FixSaathi MVP: setup and deploy

Total time: about 15 minutes locally, plus 10 minutes for Cloud Run.

## 1. Get a Gemini API key (2 min)
1. Open https://aistudio.google.com/apikey and click **Create API key**.
2. Copy the key. Do not commit it or paste it in chats.

## 2. Run on your laptop (5 min)
Needs Node.js 20 or newer (`node -v`).
```bash
cd app
npm install
cp .env.example .env        # then paste your key after GEMINI_API_KEY=
npm run local
```
- Technician app: http://localhost:8080 (camera and mic work on localhost)
- Manager dashboard: http://localhost:8080/dashboard

Check http://localhost:8080/api/health: `"ai": true` means the key is loaded.

**UI test without a key:** `npm run rehearsal` runs a scripted session with an orange "REHEARSAL MODE" banner. Use it only to test the screens, never as the real demo.

**Tests:** `npm test` checks the safety gate, diagnosis fallback, report and escalation (6 tests).

## 3. Use it on a phone
Browsers only allow camera and mic on **https** (or localhost). Two options:
- **Best:** deploy to Cloud Run (step 4). You get an https URL that works on any phone.
- **Quick:** on the same Wi-Fi, run `npx localtunnel --port 8080` or use `ngrok http 8080`, then open the https link on the phone.

## 4. Deploy to Cloud Run, Mumbai (10 min)
Needs the gcloud CLI, logged in (`gcloud auth login`), and a Google Cloud project with billing or credits.
```bash
cd app
export GEMINI_API_KEY=your_key
./deploy.sh YOUR_PROJECT_ID tensor2026     # second argument = optional access code
```
The script enables the APIs, creates Firestore in asia-south1, stores the key in Secret Manager, and deploys with a long timeout and session affinity for live WebSocket sessions. It prints the URL.
- Technician app: `https://<url>/`
- Dashboard: `https://<url>/dashboard?code=tensor2026`

## 5. If something breaks
| Problem | Fix |
|---|---|
| "Could not connect to Gemini Live" | Check the key. Set another live model: `GEMINI_LIVE_MODEL=gemini-3.1-flash-live-preview` (the server also tries fallbacks automatically). |
| No voice from the phone | Tap the screen once (browsers block audio until a tap) and turn up the volume. |
| It keeps interrupting itself | Use headphones, or mute the mic (🎙️) while it talks. |
| Noisy venue | Type in the text box; it works the same. |
| Diagnosis or report agent fails | The app falls back to the knowledge base and a structured report, so the demo continues. Check `GEMINI_AGENT_MODEL`. |
| Camera black on laptop | Allow camera in the browser, close other apps using it. |

## How it works
```
Phone (camera 1 fps + mic 16 kHz) ──WebSocket──▶ Cloud Run (Node)
                                                  ├─ Gemini Live: sees, listens, talks back (24 kHz audio)
                                                  ├─ Safety gate: blocks risky steps until power-off + tester confirmed
                                                  ├─ Diagnosis agent (Gemini API, JSON) + fault knowledge base
                                                  ├─ Part locator (Gemini returns box_2d, app draws the marker)
                                                  ├─ Report agent (Gemini API, structured JSON)
                                                  └─ Firestore ──SSE──▶ Manager dashboard (live)
```
Files: `src/server.js` (relay + API), `src/session.js` (tools and safety gate), `src/agents.js` (agents), `src/prompts.js`, `knowledge/faults.json`, `public/` (apps).
