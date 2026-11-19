# Building FixSaathi with Google's tools (AI Studio + Antigravity)

Use this so every part of the build visibly runs through Google's platforms, which is what the judges score.

## Rule check first (5 minutes, today)
Read the round-2 email and the Hack2skill event page for:
- Must the product be **built during the event**, or can you bring code you started before?
- Must it be built **in AI Studio or Antigravity** specifically?
- Must it be **deployed on Google Cloud**?

| If the rules say… | Do this |
|---|---|
| Pre-built code is allowed | Open this repo in **Antigravity** (Path A) and keep building there. |
| Everything must be built at the event | Leave this repo's app code aside. At the event, generate the app fresh with **AI Studio Build** (Path B) using the prompts below, and use this repo only as your reference and plan. |
| Not sure | Ask the organisers or a mentor in the first hour, and say which path you're on. |

## Path A: Antigravity (recommended if pre-built code is allowed)
1. Install Google Antigravity and sign in with your Google account.
2. **Open Folder** → the cloned `FixSathi/app` folder.
3. In the Antigravity agent panel, paste:
   > Read SETUP.md and the src/ folder. Install dependencies, create .env from .env.example (I will paste the Gemini key), run the tests, then start the app with `npm run local` and open http://localhost:8080.
4. For every change at the event, ask the Antigravity agent, for example:
   > Add a Kannada language option: update the language dropdown in public/index.html and liveSystemInstruction in src/prompts.js. Run npm test after.
   > Deploy this app to Cloud Run in asia-south1 using deploy.sh. My project ID is ____.
5. Take 2–3 screenshots of Antigravity working on the project for the deck (Google AI Tools slide).

## Path B: AI Studio Build (if it must be built at the event)
1. Open https://aistudio.google.com → **Build**.
2. Paste the prompt below, let it generate, then test in the preview with your camera.
3. Use **Deploy to Cloud Run** in AI Studio to get an https link.
4. Iterate with the follow-up prompts below.

**Build prompt:**
```
Build "FixSaathi", a mobile-first web app that is a live AI repair copilot for Indian field technicians, using the Gemini Live API (audio + camera video in, audio out).

Technician screen:
- Start form: technician name, customer/site, optional complaint, language (Hinglish or English).
- Live view: rear camera preview; send 1 JPEG frame per second and 16 kHz PCM mic audio to Gemini Live; play the 24 kHz audio reply; show live captions and a conversation log; a text box for noisy places; mute button; "Finish job" button.
- A red "Repair steps locked" badge that turns green only when safety is confirmed.
- Cards for: likely causes, a marked-part snapshot (draw the bounding box returned by Gemini on the latest frame), numbered steps.

Gemini Live system instruction: [paste the full text from app/src/prompts.js → liveSystemInstruction]

Function calling tools (declare them on the Live session and handle them in code):
- confirm_safety(power_off_confirmed, tester_checked, checks[]): unlocks steps only if both booleans are true.
- get_diagnosis(appliance, brand_model, symptom, observations): call gemini-3.6-flash with JSON output {causes:[{cause, likelihood, check}], next_check, escalate}, using the fault knowledge base JSON I provide.
- locate_part(part): call Gemini on the latest frame to return box_2d [ymin,xmin,ymax,xmax] 0-1000; show it on screen.
- give_step(step_number, instruction, needs_power_off): if needs_power_off is true and safety is not confirmed, return BLOCKED and shake the lock badge; otherwise show the step.
- escalate_to_senior(reason)
- complete_job(outcome, fault_found, parts_replaced[], notes): call Gemini to write a JSON service report (appliance, complaint, fault_found, root_cause, work_done[], parts_used[], safety_checks[], outcome, first_time_fix, customer_summary), save it with before/after photos, and show it.

Manager dashboard page: live list of jobs with technician, appliance, fault, safety confirmed, unsafe steps blocked, status; KPI cards for jobs today, first-time-fix rate, safety-confirmed rate, live/escalated; click a job to see the full report, photos, diagnosis and transcript.

Keep the API key on the server side. Clean Google-style design: white cards, blue primary, green/red status chips.
```
Then paste `app/knowledge/faults.json` when it asks for the knowledge base.

**Follow-up prompts:**
- "Store jobs in Firestore instead of memory, collection 'jobs', and update the dashboard live."
- "Add session resumption and sliding-window context compression to the Live session so long repairs don't disconnect."
- "Make the safety lock enforced in code, not only in the prompt, and log every blocked step on the job."

## AI Studio, whichever path you take
- **API key:** https://aistudio.google.com/apikey
- **Prompt testing:** Stream mode, paste the system instruction from `src/prompts.js`, point at a fan, and tune the wording until replies are short and safety-first. Copy the final version back into the app.
- Screenshot AI Studio testing for the deck.

## Google stack you can claim on stage (all real in the app)
Gemini Live API · Gemini API (diagnosis, part locator and report agents with JSON output and function calling) · Google AI Studio · Google Antigravity · Cloud Run (asia-south1) · Firestore · Secret Manager · Cloud Build.
Gemma (offline) and Nano Banana (step cards) are **roadmap**: say so, unless you build them at the event.
