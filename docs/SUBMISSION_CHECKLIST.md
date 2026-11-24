# Final submission checklist

The submission window opens at 6:00 PM on 20 Nov and closes at 8:00 AM on 21 Nov. **You get one submission per team.**

## Before 6 PM
- [ ] **Gemini key on Render.** Create a **new** key in AI Studio, then go to Render > fixsaathi > Environment > `GEMINI_API_KEY`, and choose Save, rebuild and deploy. Never paste the key in chat.
- [ ] Open https://fixsaathi.onrender.com/health and check that it shows `"status": "ok"`, `"database": "ok"`, `"storage": "database"` and `"configured": true`.
- [ ] Open `/demo` and start one demo scenario, so you know the fallback works if Gemini fails while you're presenting.
- [ ] **Keep it awake.** Add a free monitor at uptimerobot.com: HTTP(s), URL `https://fixsaathi.onrender.com/health`, every 5 minutes. Or switch Render to Starter (about $7/month).
- [ ] **Smoke test in an incognito window:** sign up, pick an appliance, send a photo, get a reply, run diagnosis, generate steps, confirm the lock blocks, confirm both statements unlock, create a report, open the Voice page.
- [ ] Delete the old API key in AI Studio, the one that was pasted in chat and WhatsApp.

## Deck (PDF)
- [ ] `02_Deck/FixSaathi_Deck.pdf` is **about 1 MB**, under the 10 MB limit.
- [ ] It opens correctly and has 17 slides.
- [ ] If the dashboard has a **required template**, move the content onto it. The editable `.pptx` is in the same folder.
- [ ] Optional: after the key is set, replace the "Sample data" screenshots on slides 5 and 7 with real ones from the live site.
- [ ] **Template:** the official template is on the participant dashboard, not in this repo. Download it and check whether it's mandatory.

## Demo video (optional)
- [ ] Record it using `03_Demo/DEMO_SCRIPT.md` and keep it **under 3:00**.
- [ ] Upload as **Unlisted** on YouTube, or to Drive with "Anyone with the link".
- [ ] Check that the link plays in an incognito window.

## Security
- [x] No `.env` file or API key in the GitHub repo (scanned before every push).
- [x] No secrets in the deck, the report or this package.
- [x] The Gemini key is only on the server. The browser never sees it.

## Submit, on the participant dashboard
- [ ] Prototype link: **https://fixsaathi.onrender.com**
- [ ] Deck: **FixSaathi_Deck.pdf**
- [ ] Video link, if you made one.
- [ ] Double-check all three, then submit once.
