# Jury deck v2 (City Buildathon)

`FixSaathi_Jury_Deck_v2_DRAFT.pdf` is the draft. Red **[FILL]** text marks what must come from real results tonight.

To finish it:
1. Replace `shots/a_live.png`, `b_steps.png`, `c_report.png` (phone, 400×800 viewport) and `d_dashboard.png` (1280×720) with screenshots from a **real Gemini run on a real fan**. The current ones are from rehearsal mode and must not be shown to the jury.
2. Fill `traction`, `field` and `roadmap[1]` in `content_v2.json` with real dashboard numbers, technician quotes and letters.
3. Build: `python3 build_v2.py content_v2.json FixSaathi_Jury_Deck_v2.pdf` (needs reportlab, pypdf, Poppins fonts).
