# FixSaathi — 90-Second Hackathon Demo Script & Judge Q&A

> **Target runtime:** 90 seconds (strictly paced for live stage / screen share).  
> **Before you step on stage:**
> - Sign in as your demo technician on Chrome/Edge (desktop 1280px or phone viewport 390px) with `/login` pre-warmed.
> - Have a sample rating-label / error-display photo (`CH38` Split AC or `E18` washer) ready in a desktop folder for Step 2.
> - Keep **Sunlight mode** handy (`Settings` or Home pill) if projector glare or outdoor lighting washes out dark mode.
> - **Offline / rate-limit backup:** Use `/demo` (**Demo: scripted sample, not live AI** scenarios) and `/lookup` (instant record search, zero AI calls). Both exercise the real server safety lock.

---

## 90-Second Demo Path

| Time | What to click / do | What to say |
|---|---|---|
| **0:00 – 0:12** | **1. Home — Speak a fault in Hindi.**<br>Tap the **Split AC** chip, then tap **Speak the fault** (or type: *"AC ठंडा नहीं कर रहा, इनडोर यूनिट में CH38 आ रहा है"* and send). | "Field technicians work alone with dirty hands and glare. On FixSaathi Home, one tap lets them speak a fault in English, Hindi, or Kannada — backed by 377 sourced repair records." |
| **0:12 – 0:25** | **2. Nameplate photo — Gemini Vision + technician edit.**<br>Open **Repair workspace** → Stage **1. Describe** → upload the AC rating-label/display photo → click **Read nameplate / code**. Show the extracted `LG` / model / `CH38` fields, edit one character if needed, and tap **Save & search records**. | "Gemini Vision reads the appliance rating label and error code directly from the photo, grounds retrieval in matching brand records, and lets the technician correct any misread field before saving." |
| **0:25 – 0:38** | **3. Grounded diagnosis + Expected readings.**<br>Click **Run diagnosis**. Show the **#1 fault** card with its **AI estimate** bar, `[record_id]` badge, tap **Why this?**, and scroll to **Expected readings**. | "Diagnosis comes from retrieved records, never invented codes: the bar is explicitly labelled *AI estimate*, *Why this?* shows exact evidence, and Expected Readings give safe reference values without ever guiding live work." |
| **0:38 – 0:50** | **4. Locked power-sensitive step.**<br>Open **4. Repair guidance** (after **Generate steps**). Point to the padlocked step (*Isolate the power to unlock*) and the red **Live / Locked** breaker panel (plus red microwave HV / solar DC arc warnings). | "Before isolation, any step that opens covers or touches wiring has its instruction withheld on the server — and SSE streaming buffers and screens every sentence before it leaves the server." |
| **0:50 – 1:05** | **5–6. Record both isolation statements → Unlock.**<br>Tick **(1) Switched off at MCB** and **(2) Checked with my own tester** in the Safety panel. Point out the breaker flip, unlock pulse, revealed step instruction, and the FixSaathi **SVG part schematic**. | "Once the technician records both statements, the server logs the timestamped audit trail, unlocks the step, shows an original SVG part diagram — clearly labelled not a photo — and resumes full guidance." |
| **1:05 – 1:17** | **7. Create & download Service Report PDF.**<br>In Stage **5. Report**, select **Fixed**, check **Fixed on this first visit**, add a note, tap **Create report**, and click **Download PDF**. | "One tap writes a customer/manager PDF containing only completed steps, safety confirmation timestamps, blocked attempts, and our disclaimer that FixSaathi cannot measure voltage." |
| **1:17 – 1:30** | **8. Public `/evaluation` benchmark page.**<br>Navigate to `/evaluation` (unauthenticated public route). Point to Held-out v2 (`94.4%` Hit@1, `MRR 0.958`) and Held-out Safety (`12/12` unsafe withheld, `11/12` safe shown, plus visible miss `hs08`). | "No black-box hype: our public `/evaluation` route renders `EVALUATION_RESULTS.json` directly — 94.4% top-1 on unseen queries, 12/12 unsafe instructions withheld, with every miss shown openly." |

---

## 10 Likely Judge Questions & Honest Answers

1. **Q: Couldn't a prompt injection or clever rephrasing trick Gemini into revealing a live electrical step?**  
   **A:** No model prompt is our security boundary. `backend/app/core/power_rules.py` and `services/safety.py` run deterministically on the server over every structured step, REST lookup, non-streaming reply, and SSE stream (`StreamScreener` holds bullets/lines until `\n` and screens prose sentences before sending deltas). The AI also has zero tools that can record safety statements.

2. **Q: How do you prove the technician actually turned off the MCB and used a tester?**  
   **A:** We don't — and we never pretend we can. Every checkbox, API response, safety panel, and PDF report carries the explicit disclaimer that these are *technician-entered statements* and FixSaathi cannot measure voltage or verify circuit isolation. Our goal is an intentional friction + audit checkpoint, not hardware interlock emulation.

3. **Q: What about checks that genuinely require power on (clamp-meter amps, board voltages)?**  
   **A:** Technicians in our 7-person pilot asked for a live-work mode, and we intentionally refused it. Instead, we added informational **Expected readings** cards (`GET /api/v1/expected-readings`) showing nominal reference ranges and what an out-of-range reading means, leaving live measurements solely to the technician's training and judgement.

4. **Q: Your 94.4% Hit@1 number — how real is that? Are you overfitting to your test set?**  
   **A:** All 36 queries in `held_out_v2` were written by our team (not harvested from production field logs) before the field-weighted ranking was run on them, using keyword + error-code channels without Gemini embeddings. On `/evaluation` and `docs/EVALUATION.md`, we separate Development (used for tuning) from Held-out v1 and Held-out v2, and list every miss (`v2-26`, `v2-29`, `v2-07`, `hs08`).

5. **Q: What happens if a technician is in a basement flat with weak internet or Gemini quota fails?**  
   **A:** Error codes and symptom lookups via Fault Finder (`/lookup`) query PostgreSQL directly without calling Gemini (still withholding locked steps on the server). During SSE streaming, if streaming fails in the browser, the client automatically falls back to standard `POST /messages`; when Gemini is unavailable or fails reading a nameplate, it returns an honest warning and lets the technician type brand/model/error code manually — never faking a reading.

6. **Q: Where do your 377 repair records come from, and are they all verified?**  
   **A:** No — only 189 come from manufacturer documentation we summarised (tagged `verified_source`); 188 are from the ODbL ApplianceDB sample or secondary archives tagged `unverified`, and 12 are FixSaathi team safety/repair guidance. The UI explicitly surfaces those verification labels instead of calling unverified data "verified".

7. **Q: How did you validate with real technicians, and isn't 7 a small sample?**  
   **A:** Yes — 7 technicians and helpers reached through personal contacts tested the app on real trade faults and rated it **4.7 / 5**. We state candidly in `README.md` and `docs/PILOT_FEEDBACK.md` that this is encouraging directional feedback, not statistical proof. Their top requests — red microwave/solar warnings, clearer part visuals, more Hindi, faster load — directly drove our updates.

8. **Q: Why build original SVG diagrams instead of pulling part photos from the web?**  
   **A:** Scraping manufacturer photos or Google Images violates licences/branding rules and risks showing the wrong PCB revision. Our 10 original FixSaathi SVG schematics are lightweight on 3G networks, licence-clean, and labelled *"Schematic diagram (FixSaathi SVG) — not a photo of your unit"*.

9. **Q: How is Google Gemini actually used beyond a thin ChatGPT wrapper?**  
   **A:** Five coordinated Gemini capabilities with strict server grounding and failover: (1) Vision rating-label & error-code extraction (`/read-nameplate`), (2) Vision component bounding-box localization (`/identify-component`), (3) Structured Pydantic JSON outputs for diagnosis & step classification (`DIAGNOSIS_SYSTEM`, `GUIDANCE_SYSTEM`), (4) Retrieval-augmented SSE chat + spoken Hindi guidance + embeddings, and (5) Live bidirectional WebSocket voice + TTS (`LIVE_SYSTEM`, `speech.py`).

10. **Q: What is still missing or weak right now?**  
    **A:** Three honest gaps: (1) ~253 of 377 records are washing-machine error codes, so AC/microwave/solar brand coverage is thinner; (2) full offline IndexedDB sync/service worker and a manager AI-latency observability panel were deferred for time — `/lookup` is zero-AI and fast, but there is no offline repair queue yet; (3) the safety filter has one conservative false positive (`hs08`: *"Make sure the inlet tap is fully open."*).
