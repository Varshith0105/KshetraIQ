# Security & Trust Policy — KshetraIQ Platform

At **KshetraIQ**, data integrity, agronomic decision safety, and infrastructure security are foundational principles. This document outlines our security architecture, vulnerability disclosure guidelines, responsible AI boundaries, and data governance practices.

---

## 🛡️ Supported Versions

Only the latest release branch and `main` receive security updates and hotfixes.

| Version | Supported | Notes |
|:---|:---:|:---|
| `v1.0.x` (`main`) | ✅ | Active support & continuous security patches |
| `< 1.0.0` | ❌ | Deprecated development prototypes |

---

## 🔒 Security Architecture & Defensive Controls

### 1. Dual-Engine Physical Safety & Zero-Hallucination
* **Agronomic Bounds Enforcement:** All AI/ML inference outputs pass through deterministic validation layers derived from ICAR and ANGRAU agronomic field guidelines. If soil parameters ($pH < 3.0$ or $pH > 10.0$, negative nitrogen/phosphorus/potassium, or unreasonable moisture) violate physical realities, requests are rejected with structured validation errors.
* **Prohibition of Fabricated Predictions:** Unlike general-purpose conversational LLMs, KshetraIQ prohibits speculative generation. Missing laboratory soil readings or unverified mandi commodities return an explicit `needs_input` operational status with corrective guidelines rather than hallucinated estimates.

### 2. Authentication, Session Management & Multi-Tenancy
* **Password Hashing:** Passwords are never stored in plaintext. They are cryptographically hashed using **Bcrypt** with dynamic work-factor salting via `passlib`.
* **Session Security:** Farmer and agronomist sessions are authenticated using secure JSON Web Tokens (JWT) signed with HMAC-SHA256 and transmitted via `HttpOnly`, `SameSite=Lax`, and `Secure` cookies to defend against Cross-Site Scripting (XSS) and token exfiltration.
* **Tenant & Dossier Isolation:** Farm assessment dossiers, soil test archives, and diagnosis records are strictly filtered by authenticated `user_id`. Direct object references (IDOR) are prevented via ownership validation middleware before any assessment report is retrieved or rendered.

### 3. Media Upload & Denial-of-Service (DoS) Protection
* **Magic-Byte Signature Verification:** Uploaded leaf images are verified by binary signature header inspections (`\xFF\xD8\xFF` for JPEG, `\x89PNG` for PNG, `RIFF...WEBP` for WebP) to prevent arbitrary file upload and malicious executable injection.
* **Bounded Chunk Streaming:** File uploads are streamed with an enforced buffer threshold capped at 10 MB (`KSHETRAIQ_MAX_UPLOAD_BYTES=10485760`). Payload size overflows immediately abort with HTTP 413 (Payload Too Large).
* **Sanitized Model Inference Sandboxing:** Image arrays are normalized and cast to fixed bounding tensors ($160 \times 160 \times 3$) prior to ResNet-50 evaluation, preventing memory leaks and buffer overflow attacks.

### 4. API & Transport Layer Hardening
* **Strict CORS Allowlisting:** Cross-Origin Resource Sharing is locked down to verified application origins (`http://localhost:3000`, `http://127.0.0.1:3000` in development, or explicit production domains). Wildcard (`*`) origins with credential allowance are prohibited.
* **Pydantic v2 Type Constraints:** All incoming payload bodies are strictly typed and sanitized using Pydantic v2 schemas with regex validations and boundary assertions to prevent injection vectors.
* **Zero Hardcoded Secrets Policy:** No production API credentials, database keys, or third-party tokens (e.g. Groq, Gemini, AGMARKNET) are committed to version control. All configuration is loaded dynamically through environment variables and validated at startup.

---

## 🚨 Reporting a Vulnerability

We welcome responsible security disclosures from developers, researchers, and agritech partners.

If you discover a security vulnerability, flaw, or potential risk in KshetraIQ:

1. **Do not create a public GitHub Issue.** Public issues expose systems before patches can be deployed.
2. Submit your findings privately via GitHub Security Advisories:
   - Navigate to **[KshetraIQ Security Advisories](https://github.com/Varshith0105/KshetraIQ/security/advisories/new)**
   - Or email the lead maintainer: `varshith.dev@example.com` (subject: `[SECURITY] KshetraIQ Vulnerability Report`)
3. **Include the following information:**
   - Affected endpoint, component, or model pipeline
   - Step-by-step reproduction instructions or Proof of Concept (PoC)
   - Assessment of potential impact (e.g., unauthorized data access, DoS, prompt injection)
   - Suggested remediation or workaround (if known)

### Our Commitment
* **Initial Acknowledgment:** Within **24 to 48 hours**.
* **Impact Assessment & Triage:** Within **3 business days**.
* **Remediation & Patch Release:** Critical vulnerabilities are patched within **7 days** with attribution provided in release notes (unless anonymity is requested).

---

## 📜 Compliance & Best Practices

* **Data Governance:** Farmer location data is utilized strictly for micro-climate sync (Open-Meteo) and regional mandi price lookup (AGMARKNET). Coordinates are never shared or sold to external third parties.
* **Audit Trail:** Model inference operations, error traces, and administrative actions are logged to local rotated logs with sensitive credentials masked.
