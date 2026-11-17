# FixSaathi: FINAL form answers (Tensor Trailblazers)
Copy each answer into the matching field. Text fields are checked against the 1024-character limit. All fields are complete.

## PROJECT SUBMISSION FORM

### Challenges (dropdown)  (23/1024)

SELECT: Open Innovation

### One sentence summary  (324/1024)

FixSaathi is a real-time AI repair copilot, built on Gemini Live, that watches through a field technician's phone camera and guides them hands-free, by voice in Hindi and English, to diagnose and fix ACs, appliances and rooftop-solar equipment correctly on the first visit, while automatically generating the service report.

### Main problem  (1014/1024)

India's AC, appliance and rooftop-solar installed base is growing far faster than skilled technicians can be trained. Room AC sales hit a record 12.5–13 million units in FY2025 (ICRA), over 50 lakh homes have added rooftop solar under PM Surya Ghar, and CEEW estimates India's need for skilled room-AC technicians will rise from 0.37 million (2022-23) to about 2 million by 2036-37. Yet most technicians are semi-skilled and learned on the job; only about one in four informal-sector AC technicians has formal AC training (CEEW). Facing an unfamiliar fault, they guess, phone a senior or search YouTube. The result is wrong diagnoses, wasted parts and repeat visits: service companies lose money, technicians lose a day's earnings and customers wait longer. Training alone cannot close this gap fast; technicians need expert help on the job. Jitendra, an AC and appliance technician in Mumbai, confirmed this: in old homes reversed wiring keeps a line live even after the switch is off, a risk a beginner can miss.

### Typical user/customer  (968/1024)

Primary user: a field technician, typically aged 20–40, who installs and repairs ACs, refrigerators, washing machines, fans, inverters or rooftop-solar systems. They work alone at customer homes and sites, carry an Android phone, are more comfortable speaking Hindi or a regional language than typing, are paid per job, and often have no senior nearby when a fault is unfamiliar.
Paying customers: organisations that employ or manage these technicians and bear the cost of repeat visits: authorised service centres of AC, appliance and solar brands; multi-brand repair companies; home-services platforms; rooftop-solar installers; and facility-management firms maintaining equipment in offices, hospitals and housing societies. Their managers want higher first-time-fix rates, faster onboarding of new technicians and reliable digital service reports.
Independent technicians form a third segment, using a low-cost individual plan to take on more jobs with confidence.

### Solution  (964/1024)

FixSaathi turns the technician's phone into an expert standing beside them. 1) See: the technician points the camera at the machine and Gemini identifies the appliance, brand and model. 2) Listen: they describe the symptom by voice in Hindi or English; the AI asks short follow-up questions. 3) Safety first: repair steps stay locked until the AI confirms power-off and other precautions. 4) Diagnose: it ranks likely faults and circles the suspect part on the photo. 5) Guide: it walks through the fix one spoken step at a time, keeping hands free, checks each step on camera and escalates to a senior when unsure. 6) Report: it auto-generates a service report with fault, parts and before/after photos for the manager's dashboard. Each repair feeds a shared fault knowledge base, so guidance improves with use. Built for Indian conditions: it runs on mid-range Android phones and understands Hinglish. Prototype: https://claude.ai/artifact/BApLcakTtnEcUWTL3KNZ9j

### Stage  (16/1024)

SELECT: Ideation

### Business model  (988/1024)

B2B SaaS, priced per technician per month:
1. Service centres and repair companies (core customer): about ₹299–₹499 per technician for live guidance, auto service reports and a manager dashboard. Avoiding even one or two repeat visits a month can cover the fee.
2. Brands (AC, appliance, solar): enterprise plans with brand-specific repair guides, a private fault knowledge base and analytics on which parts fail by model and region, to cut warranty costs and improve products.
3. Independent technicians: freemium, with a few free guided repairs each month, then a low fee; this builds bottom-up adoption.
Additional revenue: commission on genuine spare parts ordered in-app and paid skill-certification courses.
Go-to-market: pilot with multi-brand service centres and rooftop-solar installers in Bengaluru, who decide fast and feel repeat-visit costs directly; then scale through home-services platforms and brand service networks, where one partnership brings hundreds of technicians.

### Competitors and difference  (1001/1024)

1. YouTube videos and service manuals: free, but generic, not specific to the machine in front of the technician, not hands-free and mostly in English.
2. Remote-expert video tools (e.g. TeamViewer Frontline): connect technicians to a human expert, but need a paid expert on every call; costly and hard to scale.
3. Field-service management software (Salesforce Field Service, Zoho FSM, Fieldproxy): handle scheduling, dispatch and tracking, but do not help diagnose or fix the fault.
4. Senior technicians on the phone: helpful but scarce, busy at peak times and unable to see the machine.
FixSaathi is an AI expert that sees the machine live, speaks the technician's language, guides hands-free with built-in safety checks and writes the report automatically, at a fraction of the cost of a human expert, and it can plug into existing service software. Moat: every guided repair adds verified fault-to-fix data by brand, model and region, a knowledge base that improves accuracy and is hard to copy.

### Target countries  (967/1024)

Primary: India. A large, fast-growing service market with a record 12.5–13 million room ACs sold in FY2025, 50 lakh+ rooftop-solar installations under PM Surya Ghar, rising ownership of refrigerators and washing machines, and a mostly informally trained technician workforce. We start in Bengaluru, expand to Mumbai, Delhi NCR, Hyderabad and Pune, then add regional languages (Kannada, Tamil, Telugu, Marathi, Bengali) to reach tier-2 and tier-3 cities.
Secondary: Southeast and South Asia (Indonesia, Vietnam, the Philippines, Bangladesh), where appliance ownership is rising quickly and technicians face the same informal training gap and multilingual needs; and the Middle East (UAE, Saudi Arabia), where heavy, year-round AC use creates high service demand and a large South Asian technician workforce already speaks Hindi or Urdu. Because the product is language- and appliance-agnostic, entering a new country mainly means adding local languages and brand data.

### How you'll use AI  (1020/1024)

AI is the core of the product, not an add-on:
1. Real-time vision: recognise the appliance, model, parts and visible faults (burns, leaks, loose wiring) from the live camera.
2. Voice conversation: hands-free, two-way guidance in Hindi and English, with more Indian languages next.
3. Diagnostic reasoning: combine what it sees with the spoken symptom to rank likely causes and choose the next test.
4. Step verification and safety: confirm each step visually and block risky actions until precautions are confirmed.
5. Part location: Gemini returns the faulty part's position; the app marks it.
6. Auto-documentation: generate a structured service report from the session.
7. Offline mode: on-device safety checklist and job notes, synced later.
8. Learning loop: anonymised repair outcomes continuously improve future diagnoses.
Early test: on photos of our own appliances, Gemini read brands and specs from labels, flagged loose fan wiring and a damp, cracked ceiling on its own, and gave safety-first Hinglish steps.

### Google AI models (checkboxes)  (104/1024)

TICK: Gemini API, Gemini Live, Gemma, Nano Banana. (Not Lyria. Gemini Omni only if you confirm it fits.)

### How you'll use the selected models  (948/1024)

Gemini Live: the core experience. It streams the technician's camera and voice in real time, recognises the machine and the spoken Hindi or English symptom, and replies with spoken, step-by-step guidance, so the technician never types or looks away from the repair.
Gemini API: our reasoning agents. A diagnosis agent ranks likely faults and chooses the next check, a safety agent blocks risky steps until precautions are confirmed, and a report agent turns each session into a structured JSON service report. Function calling connects them to the fault knowledge base, spare-part lookup and brand manuals.
Nano Banana: creates visual step cards for complex repairs. To mark the faulty part, Gemini returns its location as box coordinates and our app draws the marker, so it is always precise.
Gemma: a lightweight on-device model for weak-network sites; it runs the safety checklist, saves job notes and photos offline, and syncs when back online.

### Development platforms (checkboxes)  (43/1024)

TICK: Google AI Studio, Google Antigravity.

### Deploy and scale on Google Cloud  (934/1024)

Backend services run as containers on Cloud Run in asia-south1 (Mumbai), autoscaling from zero to thousands of concurrent repair sessions, so we pay only for use. A session service on Cloud Run securely relays live audio/video to Gemini Live, with Vertex AI for production model access, quotas and monitoring. Firestore stores technicians, jobs, reports and the fault knowledge base in real time, with data isolated per service company; Firebase Authentication handles login and Firebase Hosting serves the manager dashboard. Cloud Storage holds repair photos and annotated images. Pub/Sub streams completed reports to dashboards and partner systems. BigQuery powers anonymised fault analytics for brands. Secret Manager protects API keys; Cloud Logging and Monitoring track latency and errors. To scale, we add regions as we enter new countries and use Google Agent Skills to plug in new appliance categories without re-architecting.

### How did you hear about the Buildathon  (21/1024)

Through social media.

### Pitch deck  (57/1024)

UPLOAD: FixSaathi_Deck.pdf (final, no placeholders left).

## STARTUP/PROJECT DETAILS FORM

### Project Team Name / Potential Startup Name  (40/1024)

Tensor Trailblazers (Startup: FixSaathi)

### Planning to build a venture?  (11/1024)

SELECT: Yes

### How many members  (1/1024)

2

### Intended Industry/Vertical  (164/1024)

SELECT (best available, in order): Field/Home Services · Consumer Durables/Electronics · Industrial/Manufacturing · Energy/Cleantech · SaaS/Enterprise Software · AI

### Founders, role/title, LinkedIn  (237/1024)

1. Prerana P Jois: Co-founder & CEO (Product, Backend & Cloud). LinkedIn: https://www.linkedin.com/in/prerana-p-jois-38b883290/
2. Priyam Thakur: Co-founder & CTO (AI & Engineering). LinkedIn: https://www.linkedin.com/in/priyamthakur275/

### Founder email IDs  (56/1024)

preranaprasannajois@gmail.com, priyamthakur275@gmail.com

### Founder bio / background / complementary skills  (991/1024)

Prerana P Jois (Co-founder & CEO; product, backend & cloud): final-year B.E. CSE, BMS College of Engineering, Bengaluru (2027). Software Developer Intern (AI/ML) at Robomanthan: production debugging, REST APIs, OpenCV/ONNX inference and a Flutter + Firebase/Firestore app. Delivered a client website for Silicon Semislice and led a Generative AI workshop at BNMIT. Strong in FastAPI, PostgreSQL, Firestore, GCP, Docker, CI/CD and testing.
Priyam Thakur (Co-founder & CTO; AI & engineering): final-year B.E. CSE, BMSCE (2027). Built NutriSense AI, a multi-tenant SaaS integrating Google Gemini with failover and validated outputs, and VisionGuard AI, a real-time computer-vision system (OpenCV, InsightFace, ONNX). Oracle Certified Agentic AI (98%).
Together we built ScamGuard (AI fraud detection, 98.9% accuracy on held-out data) and Kairon AI, a Gemini learning platform (Thales Hackathon 2025). Priyam leads Gemini and vision; Prerana leads backend, cloud, testing and customer discovery.

### How long working as a team  (17/1024)

SELECT: 1-2 years
