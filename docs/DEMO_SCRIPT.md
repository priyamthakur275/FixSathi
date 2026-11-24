# FixSaathi: 3-minute demo script

**Scenario:** a ceiling fan was humming and running slow, and now there are burn marks on the ceiling around the hook. It shows vision, a safety-first answer, the server-side safety lock and the automatic report in one story.

**Use:** the live site, https://fixsaathi.onrender.com, with real Gemini. Record only after the Gemini key is set and a test chat replies.

**Photo:** `backend/app/demo/ceiling_fan_burn.jpg` in the repo. It's the team's own photo.

**Target length:** 2:50, which leaves 10 seconds of margin under the 3:00 limit.

---

## Before you record (10 minutes)

1. Open the site in Chrome **2 minutes before** recording so the server is awake.
2. Sign in with a clean demo account, for example "Prerana P Jois", org "Tensor Trailblazers".
3. Run the whole flow once as a rehearsal. AI replies can take 10 to 40 seconds.
4. Start a **new session** for the real take.
5. Set Chrome zoom to 110% and hide bookmarks with Cmd+Shift+B. Close other tabs and turn on Do Not Disturb.
6. Record with QuickTime (File > New Screen Recording) or OBS at 1920×1080, with your microphone on.
7. **Cut the waiting time in editing.** Any spinner longer than about 3 seconds gets trimmed. Add a small "AI response time shortened" caption the first time you cut. That keeps the edit honest.

---

## Script

| Time | Screen | Mouse and actions | Narration | On-screen text |
|---|---|---|---|---|
| 0:00–0:20 | Deck slide 2 (problem), or a photo of a technician | None | "Most appliance technicians in India learned on the job. When they meet an unfamiliar fault, they guess, and they work alone next to live electricity. Wrong guesses mean wasted parts, repeat visits and real danger." | *Learned on the job. Working alone. Live electricity.* |
| 0:20–0:40 | FixSaathi home screen | Hover over the appliance tiles | "FixSaathi puts an expert in the technician's phone. Pick the appliance, describe the problem in Hindi or English, show a photo, and get guided, safe steps and a finished service report." | *FixSaathi: an AI repair copilot* |
| 0:40–1:05 | Home, then chat | Click **Ceiling fan**. Click the photo button and attach the burnt-fan photo. Type: *"ceiling fan humming aur slow tha, ab ceiling par burn marks hain. kya inspect karun?"* Press Enter. **Cut the wait.** | "Here's a real job: the fan was humming, and now there are burn marks on the ceiling. I add the photo and ask in Hinglish." | *Real Gemini, live* |
| 1:05–1:25 | Gemini's reply | Slowly scroll the reply | "Gemini reads the photo, spots the burn marks and calls out likely burnt wiring. Before anything else, it tells me to switch off the MCB and check with my tester, and it recommends a senior technician." | *Vision + safety-first advice* |
| 1:25–1:50 | Repair workspace | Click **Open repair workspace**. Click **Run diagnosis** and cut the wait. Point at the faults, their confidence and the "Backed by repair records" tag. | "In the workspace, FixSaathi ranks likely causes. Each one is backed by matching records from our repair knowledge base, with sources, and marked as an AI estimate, not a fact." | *Grounded in 377 repair records* |
| 1:50–2:15 | Steps and safety panel | Click **Generate steps** and cut the wait. Click the checkbox on the locked "Open the canopy" step and show the refusal. | "Now the important part. Any step that needs the power off is locked by the server. Its instructions aren't even sent to the phone. Watch: the server refuses." | *Locked on the server, not in a prompt* |
| 2:15–2:30 | Safety panel | Tick **power off**, then tick **tester checked**. The steps unlock. | "Only when I record both statements, power off and tester checked, do the steps unlock. The AI can't skip this, and every attempt is logged." | *Both statements, then unlock* |
| 2:30–2:45 | Report | Mark steps done. Choose **Escalated**, add a note, click **Create report**, then scroll the report. | "When I'm done, the service report writes itself: issue, diagnosis, steps performed, parts and recorded safety statements, ready for the manager." | *Auto service report* |
| 2:45–2:55 | Deck closing slide | None | "FixSaathi: every technician gets a safe, smart saathi. Built on Google Gemini, live today at fixsaathi.onrender.com." | *fixsaathi.onrender.com* |

**Optional, only if you have time:** a 10-second clip of the Voice page. Say it plainly: *"Voice runs on the browser's speech recognition with Gemini answering."* Don't call it Gemini Live. The Live relay is built, but your key doesn't have a Live model.

---

## If Gemini fails while you're recording

Open **Demo Scenarios** in the sidebar and choose **Ceiling fan: burn marks around the hook**. Every screen is labelled "Demo scenario: scripted sample, not live AI". Say that out loud, for example: *"This is our labelled demo mode, with scripted content. The safety lock you see is the real server."* Never present a demo scenario as live AI.

## Claims you can make, and claims you must not

**Say:**
- It's built on Google Gemini.
- It's grounded in 377 repair records across six appliances, each with its source. Gemini is used through its API; we haven't fine-tuned a model.
- The safety lock is enforced on the server.
- Every attempt is logged.
- It's live on Render, with a Neon database.

**Don't say:**
- That it uses Gemini Live streaming in this demo.
- Any accuracy percentage.
- Customer numbers.
- That it's on Cloud Run.
- That FixSaathi verifies the power is off. It records the technician's own statements.

---

## Upload

1. Export as MP4 at 1080p. Check that it's **under 3:00**.
2. Upload to YouTube as **Unlisted**, or to Google Drive with sharing set to **Anyone with the link: Viewer**.
3. Open the link in an incognito window to confirm it plays without a login.
