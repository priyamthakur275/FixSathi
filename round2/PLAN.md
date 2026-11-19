# Bengaluru City Buildathon plan (20–21 Nov): Tensor Trailblazers

**Goal:** walk in with a working app, and spend the event making it reliable, real and well pitched. Do not start new features after Day 1 evening.

## Official schedule (from the shortlist email)
- **Venue:** Total Mall, Koramangala 2nd Block, Bengaluru 560068 (opposite Madiwala police station). Arrive **8:00–9:00 AM**; programme starts **9:00 AM**, both days.
- **Day 1 (20 Nov): Ideate and design:** kick-off, hands-on time with Google AI tools, problem selection, mentor rounds.
- **Day 2 (21 Nov): Build and showcase:** build and submit the product, present to the jury, shortlist announcement.
- Max **2 members** attend. Google Cloud credits are for learning and codelabs; **Google AI Pro** is for the prototype build, with a 24-hour window (12 h to redeem + 12 h to build).

## Today (19 Nov)
| Time | Who | Task |
|---|---|---|
| Now | Prerana | **Fill the RSVP form** (team leader only). Use exactly the registration details: team name, names, emails, phone numbers. |
| Before 4:30 PM | Priyam | Get a Gemini API key, run the app locally (`app/SETUP.md`), test with a real fan. Note what breaks. |
| Before 4:30 PM | Prerana | Set up the Google Cloud project; check which billing/credits you can use for Cloud Run. |
| **4:30 PM** | Both | **Join the virtual prep session** (participant dashboard → Interaction). Ask the questions below. |
| Evening | Both | Decide Path A or B (`GOOGLE_TOOLS.md`) based on the answers. Practise the pitch twice. Pack the bag. |

**Ask in the prep session (or a mentor at 9 AM tomorrow):**
1. Can we bring code we started before the event, or must the product be built on Day 2?
2. On Day 1 "problem selection": can we keep our own Open Innovation idea (FixSaathi), or must we pick from given problem statements?
3. Must the product be built in AI Studio or Antigravity specifically, and deployed on Google Cloud?
4. What exactly do we submit on Day 2 (link, repo, video, deck)? Any time limit for the jury pitch?
5. When should we redeem Google AI Pro so the 12-hour build window covers Day 2?

**Bring:** 2 phones + chargers + power bank, laptops + chargers, wired earphones (for noise), a mobile hotspot (venue Wi-Fi fails), a small fan or fan capacitor if allowed, college IDs, a printed one-page summary.

## Day 1 (20 Nov): ideate and design
| Time | Focus |
|---|---|
| 9:00 | Kick-off. Confirm the rules with organisers (questions above). |
| Tools session | Do the hands-on with AI Studio / Antigravity; set up the project in the tool you'll use (Path A or B). |
| Problem selection | Lock FixSaathi (if allowed). Sharpen the scope: **fan + AC + MCB**, safety lock, report, dashboard. |
| Mentor rounds | Show the plan and ask: "What would make this a winner for the jury?" Note the feedback. |
| Evening | If building is allowed today: get the core loop (camera + voice + safety lock) working and deployed. Test on venue internet and the hotspot. |

## Day 2 (21 Nov): build and showcase
| Time | Focus |
|---|---|
| Morning | Build or finish: diagnosis, part marking, report, dashboard. Deploy to Cloud Run. Run 5+ real test repairs. |
| Before submission | Freeze features. Record a 60 s real backup video. Update the deck with real screenshots and your real test count. Submit early. |
| Jury | Follow `PITCH_AND_DEMO.md`. Priyam runs the demo, Prerana speaks. |

## Only if time is left (in this order)
1. Kannada or Tamil voice option (one line in `prompts.js`).
2. Escalation call button on the dashboard.
3. Nano Banana visual step card for one repair.
4. Offline Gemma checklist (keep it for the roadmap slide otherwise).

## Rules for the team
- Never demo rehearsal mode as real AI. If the live AI fails on stage, play the recorded real video and say so.
- Every number in the pitch must be real (from your test runs) or sourced (ICRA, CEEW, MNRE).
- One feature working perfectly beats five half-working.
