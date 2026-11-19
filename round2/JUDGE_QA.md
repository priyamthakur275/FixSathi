# Likely judge questions and strong answers

**1. Why can't technicians just use YouTube or call a senior?**
YouTube is generic and not about the machine in front of them, and it needs hands and eyes. Seniors are few and busy at peak season. FixSaathi sees the actual machine, talks hands-free in their language and is available on every job.

**2. What if the AI gives a wrong or dangerous instruction?**
Three layers. A safety gate in code blocks any step that touches wires until power-off and a tester check are confirmed; the model cannot skip it. Steps are short and verified on camera one at a time. And the agent escalates to a senior for gas, PCB or burnt wiring. Every session is logged for the manager.

**3. How is this different from just using Gemini in the app?**
Gemini is the engine. We add the product: enforced safety, a fault knowledge base from real technicians, part marking, structured service reports, and a manager dashboard that service companies pay for. Plus the data loop: every repair improves the knowledge base.

**4. Who pays, and why?**
Service centres and repair companies. A repeat visit costs them fuel, a technician's half day and a customer complaint. At ₹299–499 per technician per month, avoiding one repeat visit covers it. Brands pay for fault analytics by model and region.

**5. How will you get the first customers?**
Pilot with two multi-brand service centres and rooftop-solar installers in Bengaluru. They decide fast and feel repeat-visit costs directly. Then home-services platforms and brand service networks, where one deal brings hundreds of technicians.

**6. What is your moat? Google could build this.**
Verified fault-to-fix data by brand, model and region, plus distribution into service networks and workflows (reports, dashboards, spare parts). Gemini is a supplier we build on; the domain data and customer relationships are ours.

**7. Cost per session? Does it scale?**
Video is sent at 1 frame per second and audio at 16 kHz to keep tokens low; the Live session uses context compression for long repairs. Cloud Run scales from zero, so we pay only for active sessions. We will measure exact cost per repair in the pilot and keep it well under the subscription price. *(Do not quote a number you have not measured.)*

**8. What about poor network on site?**
Planned Gemma on-device mode: the safety checklist and job notes work offline and sync later. Live guidance needs data, and most urban job sites have 4G.

**9. Privacy: you record customers' homes.**
Only the camera frames needed for the repair are processed; photos are stored per service company, isolated in Firestore, and used only in anonymised form for analytics. We will add a customer consent step before recording.

**10. What did you validate?**
Real appliance photos tested on Gemini (it read labels and spotted loose wiring and a damp ceiling on its own), a working AC and appliance technician in Mumbai reviewed the guidance and added safety knowledge, and the working MVP you just saw. *(Add your real test-run count.)*

**11. Why you two?**
Priyam has shipped Gemini-based SaaS and real-time computer vision. Prerana builds backend and cloud systems with Firestore and GCP, and talks to the technicians. Together we have built and shipped AI products for over a year.

**12. What is next in 3 months?**
Pilot with 2 service centres and about 20 technicians, measure first-time-fix rate and repeat visits, add Kannada and Tamil, and expand the knowledge base to the top 20 faults.
