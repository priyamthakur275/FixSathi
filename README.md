# FixSaathi

A real-time AI repair copilot for field technicians, built on Gemini Live. It watches through the technician's phone camera and guides them hands-free, in Hindi or English, to diagnose and fix ACs, home appliances and rooftop-solar equipment on the first visit, then writes the service report.

Team **Tensor Trailblazers** (Prerana P Jois, Priyam Thakur) for Google's Startup Buildathon India 2026.

## Repository layout
- `deck/FixSaathi_Deck.pdf`: the idea-stage pitch deck on the official template (13 slides)
- `deck/photos/`: real appliance photos used for the Gemini tests
- `prototype/index.html`: clickable prototype of the MVP flow (AI responses are scripted). Open it in a browser.
- `docs/`: submitted form answers and the Gemini test PDFs
- `scripts/`: deck builder (`build.py` + `content.json`) and the form-answer generator

## How it works
1. **See:** Gemini Live identifies the appliance, brand and model from the camera.
2. **Listen:** the technician describes the fault by voice.
3. **Safety first:** repair steps stay locked until power-off is confirmed.
4. **Diagnose:** likely faults are ranked, and the suspect part is marked.
5. **Guide:** one spoken step at a time, each checked on camera.
6. **Report:** an automatic service report goes to the manager dashboard.

## Planned stack
Gemini Live, Gemini API (diagnosis, safety and report agents), Nano Banana, Gemma (offline), Google AI Studio, Antigravity, Cloud Run (asia-south1), Firestore, Firebase Auth/Hosting, Cloud Storage, Pub/Sub, BigQuery, Vertex AI and Secret Manager.

## Rebuild the deck
```bash
pip install reportlab pypdf
python scripts/build.py   # needs the official template PDF and fonts
```
