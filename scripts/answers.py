A = {}
P = "PROJECT SUBMISSION FORM"
S = "STARTUP/PROJECT DETAILS FORM"

A[(P, "Challenges (dropdown)")] = "SELECT: Open Innovation"
A[(P, "One sentence summary")] = (
"FixSaathi is a real-time AI repair copilot, built on Gemini Live, that watches through a field technician's phone camera and guides them hands-free, by voice in Hindi and English, to diagnose and fix ACs, appliances and rooftop-solar equipment correctly on the first visit, while automatically generating the service report.")
A[(P, "Main problem")] = (
"India's AC, appliance and rooftop-solar installed base is growing far faster than skilled technicians can be trained. Room AC sales hit a record 12.5–13 million units in FY2025 (ICRA), and CEEW estimates India's need for skilled room-AC technicians will grow from 0.37 million (2022-23) to about 2 million by 2036-37. Today most technicians are semi-skilled and trained on the job; only about one in four informal-sector AC technicians has received formal AC training (CEEW). Faced with an unfamiliar model or fault, they guess, call a senior or search YouTube. The result: wrong diagnoses, wasted parts and repeat visits, which cost service companies money, cost technicians a day's earnings and leave customers waiting. Service reports are often handwritten or skipped, so brands never see real failure patterns. Classroom training alone cannot close this gap at the speed the market needs.")
A[(P, "Typical user/customer")] = (
"User: a field technician aged 20–40 who installs and repairs ACs, refrigerators, washing machines, inverters or rooftop-solar systems. They work alone at customer sites, use an Android phone, prefer speaking Hindi or a regional language to typing, and are paid per job.\n"
"Paying customer: organisations that employ or manage these technicians: authorised service centres of AC, appliance and solar brands; multi-brand service companies; home-services platforms; rooftop-solar installers; and facility-management firms maintaining equipment in offices, hospitals and housing societies. Independent technicians can use a low-cost individual plan.")
A[(P, "Solution")] = (
"FixSaathi turns the technician's phone into an expert standing beside them. (1) The technician points the camera at the machine; the AI identifies the appliance and model. (2) They describe the symptom by voice in Hindi or English; the AI asks short follow-up questions. (3) It ranks likely faults and highlights the suspect part on a photo. (4) It guides the repair one step at a time by voice, so hands stay free. A safety step always comes first (power off, capacitor discharge), each step is checked on camera before moving on, and it tells the technician when to escalate to a senior. (5) At the end it auto-generates a service report with the fault, parts used and before/after photos for the service centre's dashboard. Every completed repair adds to a shared fault knowledge base, so guidance gets more accurate with use. Clickable prototype: https://claude.ai/artifact/BApLcakTtnEcUWTL3KNZ9j")
A[(P, "Stage")] = "SELECT: Ideation"
A[(P, "Business model")] = (
"B2B SaaS priced per technician:\n"
"1. Service centres and service companies: ~₹299–₹499 per technician per month for live guidance, auto service reports and a manager dashboard. Avoiding even one or two repeat visits a month can cover the fee.\n"
"2. Brands (AC, appliance, solar): enterprise plans with brand-specific repair guides, a private fault knowledge base and fault analytics by model and region.\n"
"3. Independent technicians: freemium, with limited free guided repairs per month, then a low monthly fee; drives bottom-up adoption.\n"
"Extra revenue: commission on genuine spare parts ordered in-app and paid skill-certification courses.\n"
"Go-to-market: start with multi-brand service centres and rooftop-solar installers in Bengaluru, who decide fast, then expand through home-services platforms and brand service networks.")
A[(P, "Competitors and difference")] = (
"1. YouTube videos and service manuals: free, but not specific to the machine in front of the technician, not hands-free and mostly in English.\n"
"2. Remote-expert video tools (e.g. TeamViewer Frontline): need a paid human expert on every call; costly and hard to scale.\n"
"3. Field-service management software (Salesforce Field Service, Zoho FSM, Fieldproxy): handle scheduling, dispatch and tracking, but do not help diagnose or fix the fault.\n"
"FixSaathi is an AI expert that sees the machine live, speaks the technician's language, guides hands-free with built-in safety checks and writes the service report automatically, at a fraction of the cost of human remote experts. Our moat: every guided repair adds verified fault-to-fix data by brand, model and region, a proprietary knowledge base that improves accuracy over time and is hard for new entrants to copy.")
A[(P, "Target countries")] = (
"Primary: India, a large, fast-growing AC, appliance and rooftop-solar service market (record 12.5–13M room ACs sold in FY2025; 50 lakh+ rooftop-solar installations under PM Surya Ghar) with a mostly informally trained technician workforce.\n"
"Secondary: Indonesia, Vietnam, the Philippines and Bangladesh (rising appliance ownership, multilingual technicians), and the UAE and Saudi Arabia (heavy AC usage, large South Asian technician workforce).")
A[(P, "How you'll use AI")] = (
"AI is the core of the product, not an add-on:\n"
"1. Real-time vision: recognise the appliance, model, parts and visible faults (burns, leaks, loose wiring) from the live camera.\n"
"2. Voice conversation: hands-free, two-way guidance in Hindi and English, with more Indian languages next.\n"
"3. Diagnostic reasoning: combine what it sees with the spoken symptom to rank likely causes and choose the next test.\n"
"4. Step verification and safety: confirm each step visually and block risky actions until precautions are confirmed.\n"
"5. Part location: Gemini returns the faulty part's position; the app marks it.\n"
"6. Auto-documentation: generate a structured service report from the session.\n"
"7. Offline mode: on-device safety checklist and job notes, synced later.\n"
"8. Learning loop: anonymised repair outcomes continuously improve future diagnoses.\n"
"Early test: on photos of our own appliances, Gemini read brands and specs from labels, flagged loose fan wiring and a damp, cracked ceiling on its own, and gave safety-first Hinglish steps.")
A[(P, "Google AI models (checkboxes)")] = "TICK: Gemini API, Gemini Live, Gemma, Nano Banana. (Not Lyria. Gemini Omni only if you confirm it fits.)"
A[(P, "How you'll use the selected models")] = (
"Gemini Live: the core experience. It streams the technician's camera and voice in real time, understands the machine and the spoken symptom in Hindi or English, and speaks back step-by-step guidance, so the technician never types or looks away.\n"
"Gemini API: our reasoning agents. A diagnosis agent ranks faults and picks the next test, a safety agent blocks risky steps until precautions are confirmed, and a report agent produces a structured JSON service report. Function calling connects them to the fault knowledge base and spare-part lookup.\n"
"Nano Banana: annotates the technician's photo by circling and labelling the faulty component, and generates visual step cards for complex repairs.\n"
"Gemma: a lightweight on-device model for offline mode in basements, rooftops and rural sites, giving basic guidance and syncing when back online.")
A[(P, "Development platforms (checkboxes)")] = "TICK: Google AI Studio, Google Antigravity."
A[(P, "Deploy and scale on Google Cloud")] = (
"Backend services run as containers on Cloud Run, autoscaling from zero to thousands of concurrent repair sessions, deployed in asia-south1 (Mumbai) for low latency in India. A session service on Cloud Run securely relays live audio/video to Gemini Live, with Vertex AI for production model access, quotas and monitoring. Firestore stores technicians, jobs, service reports and the fault knowledge base in real time; Firebase Authentication handles technician and manager login; Firebase Hosting serves the manager dashboard. Cloud Storage holds repair photos and annotated images. Pub/Sub streams completed reports to dashboards and partner systems. BigQuery powers anonymised fault analytics for brands. Cloud Logging and Monitoring track latency and errors. As we expand to new countries, we add regions and use Google Agent Skills to plug in new appliance categories without re-architecting.")
A[(P, "How did you hear about the Buildathon")] = "Through social media."
A[(P, "Pitch deck")] = "UPLOAD: FixSaathi_Deck.pdf (final, no placeholders left)."

A[(S, "Project Team Name / Potential Startup Name")] = "Tensor Trailblazers (Startup: FixSaathi)"
A[(S, "Planning to build a venture?")] = "SELECT: Yes"
A[(S, "How many members")] = "2"
A[(S, "Intended Industry/Vertical")] = "SELECT (best available, in order): Field/Home Services · Consumer Durables/Electronics · Industrial/Manufacturing · Energy/Cleantech · SaaS/Enterprise Software · AI"
A[(S, "Founders, role/title, LinkedIn")] = (
"1. Prerana P Jois: Co-founder & CEO (Product, Backend & Cloud). LinkedIn: https://www.linkedin.com/in/prerana-p-jois-38b883290/\n"
"2. Priyam Thakur: Co-founder & CTO (AI & Engineering). LinkedIn: https://www.linkedin.com/in/priyamthakur275/")
A[(S, "Founder email IDs")] = "preranaprasannajois@gmail.com, priyamthakur275@gmail.com"
A[(S, "Founder bio / background / complementary skills")] = (
"Prerana P Jois (Co-founder & CEO; product, backend & cloud): final-year B.E. CSE, BMS College of Engineering, Bengaluru (2027). Software Developer Intern (AI/ML) at Robomanthan: production debugging, REST APIs, OpenCV/ONNX inference and a Flutter + Firebase/Firestore app. Delivered a client website for Silicon Semislice and led a Generative AI workshop at BNMIT. Strong in FastAPI, PostgreSQL, Firestore, GCP, Docker, CI/CD and testing.\n"
"Priyam Thakur (Co-founder & CTO; AI & engineering): final-year B.E. CSE, BMSCE (2027). Built NutriSense AI, a multi-tenant SaaS integrating Google Gemini with failover and validated outputs, and VisionGuard AI, a real-time computer-vision system (OpenCV, InsightFace, ONNX). Oracle Certified Agentic AI (98%).\n"
"Together we built ScamGuard (AI fraud detection, 98.9% accuracy on held-out data) and Kairon AI, a Gemini learning platform (Thales Hackathon 2025). Priyam leads Gemini and vision; Prerana leads backend, cloud, testing and customer discovery.")
A[(S, "How long working as a team")] = "SELECT: 1-2 years"

import json as _j
for _k,_v in _j.load(open("expanded.json")).items():
    A[(P,_k)] = _v
out = ["# FixSaathi: FINAL form answers (Tensor Trailblazers)\n",
       "Copy each answer into the matching field. Text fields are checked against the 1024-character limit. All fields are complete.\n"]
cur = None
for (form, q), a in A.items():
    if form != cur:
        out.append(f"\n## {form}\n"); cur = form
    n = len(a)
    flag = "" if n <= 1024 else "  ⚠ OVER LIMIT"
    out.append(f"\n### {q}  ({n}/1024){flag}\n\n{a}\n")
    assert n <= 1024, (q, n)
open("FixSaathi_Form_Answers.md", "w").write("".join(out))
print("ok", max(len(a) for a in A.values()))
