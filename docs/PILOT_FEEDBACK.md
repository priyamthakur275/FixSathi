# Pilot feedback from technicians

Seven working technicians and helpers tried the live app in November 2026 and sent their feedback by message. Each tried a real fault from their own trade. Names are withheld unless the person agrees to be named. The messages were written in Hinglish; what is quoted below is paraphrased into English.

| # | Trade | Fault they tried | Rating |
|---|-------|------------------|--------|
| 1 | AC repair | Split AC: indoor unit runs, outdoor does not | 4.8 / 5 |
| 2 | Washing machine repair | Top-load machine not draining | 4.5 / 5 |
| 3 | Electrician (15 years, fans and wiring) | Ceiling fan running slow | 4.5 / 5 |
| 4 | AC and RO technician | Inverter AC and RO purifier | 4.7 / 5 |
| 5 | Helper (1 year, fridge and AC) | Fridge not cooling | 5.0 / 5 |
| 6 | Microwave and fridge repair | Microwave not heating | 4.8 / 5 |
| 7 | Solar installer | Rooftop inverter showing zero generation | 4.8 / 5 |

**Average: 4.7 / 5 across 7 testers** (33.1 / 7 = 4.73).

## What worked

- **Diagnoses matched their experience.** Capacitor and contactor (AC), drain pipe and drain motor (washer), capacitor and bearing (fan), membrane and flow restrictor (RO), magnetron and diode (microwave), DC isolator and string voltage (solar) were all called correct.
- **The safety lock got the most praise** for newer technicians. One helper said he had already received an electric shock once, and that the "MCB off, then test with a tester" step felt right to him.
- **Voice input** was liked for jobs where hands are dirty.
- Experienced technicians said they need it less, but it suits people who are still learning.

## What they asked for

1. **Slow first load.** One tester waited about 40 seconds, another also called it slow. The free hosting plan sleeps when idle. Waiting this long in a customer's home is awkward.
2. **Safety lock is too strict for live measurements.** Clamp-meter current checks and PCB voltage checks need the supply on, but the lock blocks them. (Related: it does not open without internet, for example in a basement flat.)
3. **Louder warnings where "MCB off" is not enough.** Microwaves keep dangerous charge in the high-voltage capacitor, and solar systems carry DC arc risk. Both warnings should be larger and in red.
4. **Less English, more Hindi/Hinglish**, and faster loading.
5. **Photos of parts**, so a newer technician can identify the part faster.
6. **More detail on common causes** in washers, such as rats cutting wires or the PCB not supplying power.

Not every request will be built. Live measurements with the supply on are left out by design: FixSaathi does not guide work on live circuits. Microwave capacitor and solar DC-arc wording, part photos and a faster first load are the ones to look at next.

## How to read this

- Seven testers is a small pilot. It shows the idea works for working technicians; it is not a statistically meaningful sample.
- The testers are people the team knows, and ratings were sent by message, not recorded by the in-app thumbs buttons. Expect some generosity in the scores.
- Every complaint above is listed, including the ones that make the product look worse.
