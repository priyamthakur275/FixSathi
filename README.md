# FixSaathi

A real-time AI repair copilot for field technicians, built on **Gemini Live**. It sees through the technician's phone camera, talks them through the repair hands-free in Hinglish or English, enforces safety before any risky step, and sends an automatic service report to the manager's dashboard.

Team **Tensor Trailblazers** (Prerana P Jois, Priyam Thakur). Shortlisted for the City Buildathon, Google Startup Buildathon India 2026.

## What's in this repo
| Folder | What it is |
|---|---|
| [`app/`](app/) | **Working MVP**: technician app, manager dashboard, Node server on Cloud Run. Start with [`app/SETUP.md`](app/SETUP.md). |
| [`round2/`](round2/) | City Buildathon kit: [Google tools guide](round2/GOOGLE_TOOLS.md), [2-day plan](round2/PLAN.md), [pitch + live demo script](round2/PITCH_AND_DEMO.md), [judge Q&A](round2/JUDGE_QA.md) |
| `deck/` | Idea-stage pitch deck (PDF) and the appliance photos used in Gemini tests |
| `prototype/` | Earlier clickable prototype (scripted) |
| `docs/` | Submitted form answers, Gemini test PDFs, app screenshots |
| `scripts/` | Deck builder and form-answer scripts |

## The MVP
- **Live guidance:** camera (1 fps) and mic stream to Gemini Live, which answers by voice in Hinglish.
- **Safety gate:** risky steps are blocked in code until power-off and a line-tester check are confirmed.
- **Diagnosis agent:** Gemini API ranks likely causes using a fault knowledge base that includes a working technician's input.
- **Part marking:** Gemini returns the part's bounding box on the latest frame, and the app draws the marker.
- **Report agent:** a structured JSON service report with before/after photos.
- **Nano Banana step cards:** a 🖼️ Picture button turns any step into a visual instruction card from the real camera frame.
- **Manager dashboard:** live job feed, first-time-fix rate, safety compliance, escalations, technician-rated accuracy, and **measured AI cost and reply time per repair**.
- **Languages:** Hinglish, English, Kannada, Tamil.
- **Google Cloud:** Cloud Run (asia-south1), Firestore, Secret Manager, Cloud Build.

```bash
cd app && npm install && cp .env.example .env   # add GEMINI_API_KEY
npm run local                                   # http://localhost:8080 and /dashboard
npm test                                        # safety gate, diagnosis fallback, report
```

Screenshots in `docs/screenshots/` were taken in rehearsal mode (scripted UI test, marked with an orange banner), not with the live AI.
