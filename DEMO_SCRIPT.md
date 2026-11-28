# FixSaathi — 90-Second Hackathon Demo Script & Judge Q&A

> **Live URL:** <https://fixsaathi-vu9s.onrender.com> (Public evaluation benchmark: <https://fixsaathi-vu9s.onrender.com/evaluation>)  
> **Target runtime:** 90 seconds (strictly paced for live stage / screen share).  
> **Stack:** Prototyped with **Antigravity**; deployed on **Render** (Docker, free plan, Singapore, auto-deploying from `antigravity-v2`) with Render free PostgreSQL (`fixsaathi-db`; also deployed temporarily on Google Cloud Run + Cloud SQL during the hackathon sprint). Uses Google Gemini `gemini-3.5-flash-lite` for chat, SSE streaming, fault diagnosis, and nameplate vision, `gemini-embedding-2` for hybrid retrieval embeddings, `gemini-3.8-live` for Live voice/video WebSocket relay, and `gemini-3.8-flash-tts` for spoken audio, all guarded by a deterministic **server-side safety guardrail**.  
> **Before you step on stage:**
> - Sign in as your demo technician on Chrome/Edge (desktop 1280px or phone viewport 390px) at `https://fixsaathi-vu9s.onrender.com` (wake `/health` beforehand if idle >15 min so cold start doesn't take ~50 s).
> - Either click **Try a sample nameplate** directly inside Stage 1 of a repair session or upload [`docs/samples/sample_nameplate.png`](docs/samples/sample_nameplate.png) (`LG Inverter Split AC LS-Q18YNZA / ERROR: CH38`).
> - Keep **Sunlight mode** handy (`Settings` or Home pill) if projector glare or outdoor lighting washes out dark mode.
> - **Offline / rate-limit backup:** Use `/demo` (behind the sidebar **Offline backup** footer link, labelled **Demo: scripted sample, not live AI**) and `/lookup` (instant Postgres search, zero AI calls). Both exercise the real server-side safety guardrail.

---

## 90-Second Demo Path

| Time | What to click / do | What to say |
|---|---|---|
| **0:00 – 0:20** | **1. Sample nameplate — Gemini Vision + confirmation gate.**<br>Open **Repair workspace** → Stage **1. Describe** → click **Try a sample nameplate** (loads `sample_nameplate.png`) → click **Read nameplate / code**. Show the extracted `LG / LS-Q18YNZA / CH38` fields, the **AI estimate** confidence badge, and tap **Confirm & use model**. | "Field technicians work alone in dim utility rooms. One tap loads a rating-label photo; Gemini Vision reads `LG LS-Q18YNZA` and error `CH38`, searches 377 sourced repair records, and requires the technician to verify the model before diagnosis unlocks." |
| **0:20 – 0:38** | **2. Hinglish symptom — grounded SSE streaming + provenance.**<br>Send a Hinglish symptom in Chat (or Stage 2), e.g.: *"AC thanda nahi kar raha, indoor unit mein CH38 aa raha hai"* and run **Run diagnosis** in Stage 2. Expand **Why this?** and **How this answer was made** (shows real `model_identifier`, latency, and retrieved `[record_id]` sources). | "Technicians message in everyday Hinglish, Hindi, or English. Replies stream word-by-word over SSE using `gemini-3.5-flash-lite`, backed only by retrieved KB records — never invented codes — and the provenance panel exposes the exact model and latency." |
| **0:38 – 0:54** | **3. Safety lock — withheld on the server.**<br>Ask for repair steps (or click **Generate steps** in Stage 4) while power is **Live / Locked**. Point to the redacted `[Power-sensitive step withheld]` block and the red **Safety panel** (plus microwave HV / solar DC arc warnings). | "Before isolation, any step that opens covers or touches wiring has its instruction stripped on the server. `StreamScreener` buffers lines on the server so locked steps never leak over SSE." |
| **0:54 – 1:14** | **4. Unlock — isolation audit + schematic.**<br>Tick **(1) Switched off at MCB** and **(2) Checked with my own tester** in the Safety panel. Point out the breaker flip to isolated, the revealed step instructions, and the FixSaathi **SVG part schematic** (and optional Stage 5 PDF report). | "Only after the technician records both isolation statements does the server log the timestamped audit event, unlock the electrical steps, and display an original SVG schematic." |
| **1:14 – 1:30** | **5. Public `/evaluation` benchmark page.**<br>Open `https://fixsaathi-vu9s.onrender.com/evaluation` (unauthenticated). Point to **Held-out v2** (`94.4%` Hit@1, `MRR 0.958`) and **Held-out Safety** (`12/12` unsafe withheld, `11/12` safe shown, plus visible miss `hs08`). | "No black-box claims: `/evaluation` renders `EVALUATION_RESULTS.json` publicly — 94.4% top-1 on unseen queries, 12/12 unsafe steps withheld, and every miss listed openly." |

---

## 10 Likely Judge Questions & Honest Answers

1. **Q: Couldn't a prompt injection or clever rephrasing trick Gemini into revealing a live electrical step?**  
   **A:** No model prompt is our security boundary — the safety lock is a deterministic **server-side guardrail**. `backend/app/core/power_rules.py` and `services/safety.py` run on the server over every structured step, REST lookup, non-streaming reply, and SSE stream (`StreamScreener` holds bullets/lines until `\n` and screens prose sentences before sending deltas). The AI also has zero tools that can record safety statements.

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

9. **Q: How is Google Gemini actually used beyond a thin wrapper?**  
   **A:** Coordinated Gemini capabilities with strict server grounding and verification on the live Render service (`gemini-3.5-flash-lite` primary for chat and structured diagnosis/vision): (1) Vision nameplate & error-display extraction (`/read-nameplate`), (2) Structured Pydantic JSON outputs for diagnosis & step classification (`DIAGNOSIS_SYSTEM`, `GUIDANCE_SYSTEM`), (3) Retrieval-augmented SSE chat + configured `gemini-embedding-2` hybrid search, (4) Live bidirectional WebSocket voice + camera relay (`gemini-3.8-live`; API endpoint verified 3/3 by `smoke_live.py`, not yet on the app screens), and (5) Spoken TTS (`gemini-3.8-flash-tts`) with browser voice fallback.

10. **Q: What is still missing or weak right now?**  
    **A:** Three honest gaps: (1) ~253 of 377 records are washing-machine error codes, so AC/microwave/solar brand coverage is thinner; (2) full offline IndexedDB sync/service worker and a manager AI-latency observability panel were deferred for time — `/lookup` is zero-AI and fast, but there is no offline repair queue yet; (3) the safety filter has one conservative false positive (`hs08`: *"Make sure the inlet tap is fully open."*).
