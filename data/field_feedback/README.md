# Field feedback, November 2026

50 working technicians tried FixSaathi on a real or recent fault of their own and answered six questions over WhatsApp
(text or voice note), collected by Priyam Thakur on 25 November 2026. The request is in the main README.

`2026-11-whatsapp.csv` has one row per reply. Names appear only where the technician agreed to be named; the other
rows keep only the city. `issues` are tags given to each complaint, so they can be counted:

| Tag | Meaning |
|---|---|
| slow_first_load | Opening the app took 30-45 seconds |
| simpler_language | Too many English words, or wanted simpler Hindi or another language |
| basic_for_experts | Fine for juniors, too basic for an experienced technician |
| live_testing | Some checks (running current, PCB voltage) need the supply on |
| brand_codes | Wanted brand-specific error codes |
| advanced_data | Wanted sensor resistance values, gas pressure charts, PCB voltages |
| unneeded_isolation | Asked to switch off the MCB for a fault with no electrical work |
| repeated_isolation | Recording isolation again each time felt slow |
| offline, photos, microwave_warning, dc_warning, voice_in_noise, missed_causes, no_time | As named |

Ratings were given out of 5 and are recorded as given. Who answered is not a random sample: they were reached through
personal contacts, so treat the numbers as early signal, not a measured result.
