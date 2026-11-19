# City Buildathon plan (20–21 Nov): Tensor Trailblazers

**Goal:** walk in with a working app, and spend the event making it reliable, real and well pitched. Do not start new features after Day 1 evening.

## Today (19 Nov), before the event: about 3 hours
| Who | Task | Done when |
|---|---|---|
| Priyam | Get a Gemini API key, run `npm run local`, test with a real fan | FixSaathi talks back in Hinglish and the safety lock works |
| Prerana | Create the Google Cloud project, link credits/billing, run `./deploy.sh` | The https Cloud Run URL opens on both phones |
| Both | Run 3 full test repairs (fan slow, AC filter, MCB trip) | Each ends with a report on the dashboard |
| Both | Record a 60 s backup video of one full run | Saved on both phones and Drive |
| Both | Read the round-2 email: venue, timing, rules, judging, what to bring | Checklist below ticked |

**Bring:** 2 phones + chargers + power bank, laptop + charger, wired earphones (for noise), a mobile hotspot (venue Wi-Fi fails), a spare ceiling-fan capacitor and a small fan or regulator if allowed, printed one-page summary, college ID.

## Day 1 (20 Nov)
| Time | Focus |
|---|---|
| First hour | Set up, confirm the deployed URL works on venue internet and hotspot. Meet mentors, ask what judges weigh most. |
| Morning | **Reliability:** run 10 test repairs, note every failure, tune `src/prompts.js` (shorter replies, clearer safety). |
| Afternoon | **Real-world proof:** add 2–3 fault entries from Jitendra to `knowledge/faults.json`. Call him for one fresh tip if possible. |
| Evening | Freeze features. Polish the dashboard demo data: run 4–5 real sessions so the KPIs look alive (all real runs, no fake rows). |

## Day 2 (21 Nov)
| Time | Focus |
|---|---|
| Morning | Pitch rehearsal ×5 with a timer. Update the deck: replace the prototype slide with screenshots of the real app and the dashboard. |
| Midday | Final deploy, test on the stage phone, charge everything. Backup video ready. |
| Pitch | Follow `PITCH_AND_DEMO.md`. Priyam drives the demo, Prerana speaks. |

## Only if time is left (in this order)
1. Kannada or Tamil voice option (one line in `prompts.js`).
2. Escalation call button on the dashboard.
3. Nano Banana visual step card for one repair.
4. Offline Gemma checklist (keep it for the roadmap slide otherwise).

## Rules for the team
- Never demo rehearsal mode as real AI. If the live AI fails on stage, play the recorded real video and say so.
- Every number in the pitch must be real (from your test runs) or sourced (ICRA, CEEW, MNRE).
- One feature working perfectly beats five half-working.
