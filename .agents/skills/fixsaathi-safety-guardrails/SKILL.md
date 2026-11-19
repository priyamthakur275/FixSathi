---
name: fixsaathi-safety-guardrails
description: Enforce electrical-safety, tool-gating and data rules when editing FixSaathi repair-copilot code (session.js, prompts.js, faults.json). Use when touching safety gates, repair steps, fault knowledge or database queries.
---
# Rules
1. Never allow a step marked needs_power_off unless confirm_safety has power_off_confirmed AND tester_checked. The check lives in code (session.js), never only in a prompt.
2. Every fault in app/knowledge/faults.json needs: id, symptoms, likely_causes, steps, and a safety note. Steps that open a panel set needs_power_off=true.
3. Language stays simple Hinglish/English; one short step at a time; never ask a technician to touch live parts.
4. Use parameterized SQL only. Never run DROP TABLE. Use snake_case table names with a primary key `id`.
5. Never log or print API keys. Secrets come from env or Secret Manager.
6. Run `npm test` after any safety-gate change; all tests must pass.
