# Security & Safety Policy

## Safety-First Architecture

FixSaathi is an AI repair copilot designed with server-enforced electrical safety guardrails:

- **Server-Side Safety Lock (`SafetyService.guard`)**: Power-sensitive repair instructions are withheld on the server until the technician records both isolation confirmations (MCB/isolator switched off and checked with their own tester). The AI has no tool or permission to bypass or record safety statements.
- **Output Screening**: AI chat and voice replies are screened sentence-by-sentence against `app/core/power_rules.py` (including Hindi/Hinglish verbs) before reaching the client.
- **Authentication & Uploads**: JWT access/refresh tokens, organisation-scoped RBAC for managers, rate-limited authentication, a per-account AI quota so one sign-up cannot use up the Gemini key, magic-byte file validation, and EXIF/location stripping on uploaded photos.
- **HTTP Hardening**: Baseline security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Strict-Transport-Security`, `Permissions-Policy`) on all API responses.

## Reporting a Vulnerability

Please report security issues privately via GitHub Security Advisories or email `priyamthakur.cs23@bmsce.ac.in` rather than opening a public issue.
