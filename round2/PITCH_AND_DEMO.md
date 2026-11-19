# Pitch and live demo (3 minutes + Q&A)

Prerana speaks, Priyam holds the phone and runs the demo. Practise until it fits in 3:00.

## 0:00–0:30 Problem (Prerana)
"India sold a record 12 to 13 million room ACs last year, and CEEW estimates we will need about 2 million skilled AC technicians by 2036, up from under 4 lakh. Most technicians learn on the job. When a fault is new, they guess, call a senior or search YouTube. The result: wrong diagnoses, wasted parts and repeat visits.
Jitendra, a technician in Mumbai we spoke to, told us something scarier: in old homes, reversed wiring keeps a line live even after the switch is off. A beginner can miss that."

## 0:30–0:45 Solution (Prerana)
"FixSaathi is a senior technician in every technician's pocket. Built on Gemini Live, it sees through the phone camera, talks in Hinglish, never unlocks a repair step until power is safely off, and writes the service report automatically. Let us show you, live."

## 0:45–2:00 Live demo (Priyam, phone mirrored to screen)
1. Open the app, tap **Start live guidance**, point at the fan.
2. Say: **"Pankha bahut slow chal raha hai."**
   FixSaathi identifies the fan and calls the diagnosis agent → **likely causes** card appears (capacitor first).
3. Say: **"Theek hai, canopy khol deta hoon."**
   → FixSaathi **stops you**: the lock stays red and it asks you to switch off the MCB and check with a tester. (If the model ever tries to give the step anyway, the safety gate in code blocks it and the lock shakes.)
   *Prerana: "This is the moment that prevents accidents. The AI cannot skip safety; it is enforced in code, not just in the prompt."*
4. Say: **"MCB off kar diya, tester se check kiya, koi line live nahi hai."**
   → Lock turns green. Ask: **"Capacitor kahan hai?"** → the part is **marked on screen**.
5. Steps appear one at a time. Say **"ho gaya"** after each.
6. Say: **"Fan ab theek chal raha hai."** → **report** pops up.
7. Switch to the laptop: the **manager dashboard** already shows the job: safety confirmed, unsafe step blocked, first-time fix, before/after photo.

## 2:00–2:40 Business and traction (Prerana)
"We sell to service centres and repair companies at about ₹299–499 per technician per month. Saving one repeat visit a month pays for it. Brands get fault analytics by model and region. Independent technicians get a freemium plan.
Every guided repair adds verified fault-to-fix data, which becomes our moat.
Validation so far: real appliance tests on Gemini, a working technician in Mumbai reviewing our steps, and [N] test repairs built this weekend." *(use your real count)*

## 2:40–3:00 Close (Prerana)
"Our next step is a pilot with two multi-brand service centres in Bengaluru, measuring first-time-fix rate and repeat visits. We are Prerana and Priyam, final-year CSE at BMSCE. FixSaathi: safe repairs, first time, in the technician's own language."

## If the demo fails on stage
- No internet: switch to the phone hotspot (have it on before you start).
- AI does not respond in 10 s: say "Live networks at events are tricky; here is the same flow recorded this morning on real hardware", and play the backup video. Do **not** use rehearsal mode.
- Too noisy: type the lines in the text box; everything else works the same.

## Demo checklist (5 minutes before)
- [ ] Phone at full brightness, volume up, Do Not Disturb on
- [ ] App open on the deployed URL, health shows AI ready
- [ ] Dashboard open on the laptop, last job visible
- [ ] Fan (or a clear fan photo on a second screen) ready
- [ ] Backup video open in the gallery
- [ ] Hotspot on
