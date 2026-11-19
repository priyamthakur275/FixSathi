# Master plan: Bengaluru City Buildathon (20–21 Nov) → Regional Showcase

**Goal:** be one of the teams the jury sends to the Regional Showcase.
**How the jury decides:** they score the *developed product*, on five things from the official criteria: founder profile, product potential, market viability, technical architecture, and how deeply Google AI powers the product.
**Our edge:** we arrive with a working, deployed product (mentors confirmed pre-built work is allowed), so we spend the event on proof, polish and pitch while others are still building.

## What will win the room (in priority order)
1. **A flawless live demo on a real fan**: voice in Hinglish, safety lock, diagnosis, part marked, report on the dashboard. Under 75 seconds, zero failures.
2. **Real-world proof no other team has**: Bengaluru technicians who tried FixSaathi, their words on video, and ideally a signed letter of interest from a service centre.
3. **Real numbers**: test repairs done, correct diagnoses, unsafe steps blocked, measured cost per repair.
4. **Deep, visible Google AI**: Gemini Live + Gemini API agents with function calling + Cloud Run + Firestore, built in AI Studio/Antigravity, with real screenshots.
5. **A tight 3-minute pitch** with a clear business model and a pilot plan.

## Roles
- **Priyam (CTO):** the app, the demo, deployment, technical Q&A.
- **Prerana (CEO):** technician and service-centre validation, deck, pitch, business Q&A.
- **Claude:** builds the new features below, fixes bugs from your error messages, updates the deck v2 from your real screenshots and numbers.

---

## TODAY (19 Nov): the most important day
| Time | Priyam | Prerana |
|---|---|---|
| 10:30–11:00 | Gemini API key (aistudio.google.com/apikey). Run the app locally (`app/SETUP.md`). | **Fill the RSVP form** (exact registration details). |
| 11:00–1:00 | Test with a real fan: does it talk, see, lock, diagnose, mark, report? Send Claude every error. | Google Cloud project + credits/billing. Run `./deploy.sh` with Priyam. Get the **https link**. |
| 1:00–3:30 | Open the project in **Antigravity**, test the AI Studio Stream prompt; take screenshots of both. Do 10 test repairs (fan slow, fan not starting, AC low cooling, MCB tripping) and log them in `TEST_LOG.md`. | **Field validation (highest impact):** visit 2–3 repair shops or service centres nearby. Let technicians try FixSaathi for 5 minutes. Ask the 5 questions below. With permission, record a 15-second video quote. Ask one owner for a **letter of interest** (template below). |
| 4:30–5:30 | **Both: join the Google virtual prep session.** Ask about submission format, pitch length and Google AI Pro timing. | |
| 6:00–8:00 | Fix today's issues; final deploy; record the **60 s backup video** of a real run. | Send Claude the real numbers, quotes and screenshots → Claude builds **deck v2**. Call Jitendra: share the link, ask for one sentence of feedback. |
| 8:00–9:30 | Both: pitch rehearsal ×3 with a timer. Pack the bag. Sleep by 11. | |

**5 questions for technicians:**
1. How often do you get a fault you're not sure about? What do you do then?
2. After using FixSaathi: was the guidance correct? Would you use it on a real job?
3. Would your company pay ₹299–499 a month for this? Would you pay ₹99 yourself?
4. What was missing or wrong?
5. Can we quote you (name or first name only)?

**Letter of interest (one paragraph; letterhead or WhatsApp is fine):**
> "[Service centre name], Bengaluru, is interested in piloting FixSaathi with our technicians for [4] weeks to measure first-time-fix rate and repeat visits. This is not a purchase commitment." Signed: name, role, phone, date.

---

## DAY 1 (20 Nov): ideate and design
| Time | Task |
|---|---|
| 8:00–9:00 | Arrive and set up. Test the deployed link on venue Wi-Fi **and** the hotspot. |
| 9:00 | Kick-off. Confirm the submission format and the jury pitch length. |
| Tools session | Use AI Studio / Antigravity hands-on; take photos and screenshots for the "Google AI depth" slide. |
| Problem selection | Lock FixSaathi (Open Innovation). Scope: fan + AC + MCB faults. |
| **Mentor rounds** | Show the live demo (30 s), then ask: *"What would stop the jury from picking us?"* Write down every answer and fix the top 2. Note the mentor's name to mention ("we improved X after mentor feedback"). |
| Evening | Improve from mentor feedback. More test repairs. Re-deploy. Pitch ×3. |

## DAY 2 (21 Nov): build and showcase
| Time | Task |
|---|---|
| Morning | **Feature freeze by 12:00.** Only bug fixes after that. |
| Midday | 5 final test runs on the stage phone. Update test numbers in the deck. Submit early (link, repo, deck, video). |
| Before jury | Demo checklist (`PITCH_AND_DEMO.md`). Hotspot on, phone at full brightness, backup video ready. |
| Jury | 3-minute pitch with the live demo, then Q&A (`JUDGE_QA.md`). |

---

## What Claude builds next (today, while you test)
1. **Cost and speed meter:** real tokens and cost per repair on the dashboard, so "what does it cost?" gets a measured answer.
2. **Technician feedback:** "Was the guidance correct?" 👍/👎 at the end of each job, giving a real accuracy % for the pitch.
3. **Nano Banana step card:** a generated visual instruction card for a step (you claimed Nano Banana in the submission, so make it real).
4. **Kannada voice option**, for the Bengaluru jury.
5. **Deck v2** for the jury, once you send real screenshots, numbers and quotes.

Gemma offline mode stays **roadmap**. Say so honestly if asked.

## Success checklist before the jury
- [ ] Deployed https link works on both phones and the venue network
- [ ] 15+ real test repairs logged, with accuracy and cost numbers
- [ ] 2+ Bengaluru technicians tried it; 1+ video quote
- [ ] 1 letter of interest from a service centre (stretch goal)
- [ ] Jitendra's feedback on the live app
- [ ] Deck v2 with real screenshots, numbers and quotes
- [ ] 60 s real backup video
- [ ] Pitch rehearsed 6+ times, under 3:00

## Risks and backups
| Risk | Backup |
|---|---|
| Venue internet fails | Phone hotspot; test it on Day 1 morning |
| Gemini Live slow or down | Backup video of a real run; the server auto-tries fallback models |
| Too noisy for voice | Wired earphones; the text box works the same |
| The model answers wrong on stage | Demo the fault you've tested most (fan slow → capacitor); never improvise a new fault on stage |
| Out of API quota | A second API key from the other teammate's account, ready in `.env` |
| Laptop dies | The dashboard also opens on the second phone |

## Never do
- Show rehearsal mode as real AI.
- Quote numbers you didn't measure, or claim features that aren't built.
- Add new features on Day 2 afternoon.
