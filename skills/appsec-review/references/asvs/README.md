# ASVS 5.0 reference data

Section files of the OWASP Application Security Verification Standard **5.0**, one file
per section, with YAML frontmatter for lookup. Cite requirements by their id without the
`V` prefix (e.g. `ASVS 8.2.2`); sections keep it (`V8.2`).

## How to use

1. Find the matching sections in the lookup table below (or match the `when_to_use`
   entries in the frontmatter of each file).
2. Read the section file — the requirement table has id, text and level.
3. Cite the most specific requirement id in the finding. Don't cite a whole chapter.
4. Requirements are levelled: **L1** baseline, **L2** standard (default for production
   web/API systems), **L3** high assurance. A gap at a level above the project's target
   level is at most `Info`.

File format:

```yaml
---
title: "V6.2 Password Security"
asvs_chapter: "V6.2"
when_to_use: [...]   # task triggers
threats: [...]       # threat categories
summary: "..."
---
| # | Description | Level |
```

The first section file of each chapter (`V1.1`, `V2.1`, …) also holds the chapter's
control objective.

## Chapters (ASVS 5.0)

| Chapter | Name | Sections in this folder |
|---|---|---|
| V1 | Encoding and Sanitization | V1.1–V1.3, V1.5 |
| V2 | Validation and Business Logic | V2.1–V2.4 |
| V3 | Web Frontend Security | V3.1–V3.7 |
| V4 | API and Web Service | V4.1–V4.4 |
| V5 | File Handling | V5.1–V5.4 |
| V6 | Authentication | V6.1–V6.8 |
| V7 | Session Management | V7.1–V7.6 |
| V8 | Authorization | V8.1–V8.4 |
| V9 | Self-contained Tokens | V9.1–V9.2 |
| V10 | OAuth and OIDC | V10.1–V10.3, V10.5, V10.7 |
| V11 | Cryptography | V11.1–V11.7 |
| V12 | Secure Communication | V12.1–V12.3 |
| V13 | Configuration | V13.1–V13.4 |
| V14 | Data Protection | V14.1–V14.3 |
| V15 | Secure Coding and Architecture | V15.1–V15.4 |
| V16 | Security Logging and Error Handling | V16.1–V16.5 |

**Not included** (irrelevant for FastAPI/React projects that consume an external IdP):
V1.4 Memory, String, and Unmanaged Code · V10.4 OAuth Authorization Server ·
V10.6 OpenID Provider · V17 WebRTC (V17.1–V17.3). If a project does run its own
authorization server or WebRTC stack, consult the upstream standard.

## Lookup — what to load for which code

| Code / topic under review | Sections |
|---|---|
| SQL/`text()`, shell/`subprocess`, LDAP, regex with user input, URL building | V1.2 |
| Rich text / HTML / Markdown / SVG input, `eval`, templates built from input, SSRF, mail headers, ReDoS | V1.3 |
| `pickle`, `yaml.load`, XML parsing, untrusted deserialization | V1.5 |
| Encoding order, double decoding, canonical form | V1.1 |
| Pydantic/Zod validation, value ranges, allowlists | V2.2 |
| Multi-step flows, state machines, prices, stock, transactions, locking | V2.3 |
| Rate limiting, anti-automation, cost-heavy operations | V2.4 |
| `Content-Type`, `nosniff`, rendering uploads/API responses in the browser, `textContent`, DOM clobbering | V3.2 |
| Cookie attributes (`Secure`, `HttpOnly`, `SameSite`, `__Host-`) | V3.3 |
| HSTS, CSP, CORS header value, Referrer-Policy, `frame-ancestors`, COOP | V3.4 |
| CSRF, CORS preflight reliance, `postMessage`, JSONP, Sec-Fetch-* | V3.5 |
| Third-party scripts/CDN assets, SRI | V3.6 |
| Open redirects, outdated client tech, HSTS preload | V3.7 |
| Generic API: content type, HTTP→HTTPS redirects, proxy headers (`X-Forwarded-*`), HTTP methods | V4.1 |
| Request smuggling, header/URI length, HTTP/2 framing | V4.2 |
| GraphQL depth/cost limits, introspection | V4.3 |
| WebSockets: WSS, Origin check, session tokens | V4.4 |
| Upload size/type/archives/pixel floods | V5.2 |
| File storage paths, executable uploads, zip slip | V5.3 |
| Downloads: `Content-Disposition`, filenames, AV scanning | V5.4 |
| Password policy, password change | V6.2 |
| Login, brute force, enumeration, default accounts, MFA requirement | V6.3 |
| Password reset, initial passwords, factor recovery | V6.4 |
| MFA, TOTP, lookup secrets, OTP lifetime | V6.5 |
| SMS/email/push out-of-band codes | V6.6 |
| WebAuthn/passkeys/client certificates | V6.7 |
| External IdP login, multiple IdPs, signature validation of assertions | V6.8 |
| Session token creation, rotation on login | V7.2 |
| Idle / absolute session timeout | V7.3 |
| Logout, session termination, "log out everywhere" | V7.4 |
| Re-authentication for sensitive changes, session listing | V7.5 |
| SSO/federated session lifetime | V7.6 |
| Authorization rules documented | V8.1 |
| Function-, object- (IDOR/BOLA) and field-level (BOPLA) authorization | V8.2 |
| Server-side enforcement, permission changes, acting on behalf of a user | V8.3 |
| Multi-tenancy, admin interfaces | V8.4 |
| JWT signature, algorithm allowlist, key sources (`jku`, `x5u`, `jwk`) | V9.1 |
| JWT `exp`/`nbf`, token type, audience | V9.2 |
| Any OAuth/OIDC flow; tokens only where needed (BFF) | V10.1 |
| OAuth client: `state`/PKCE, mix-up, scopes | V10.2 |
| API validating IdP access tokens (resource server) | V10.3 |
| OIDC login in the app (relying party): `nonce`, `sub`, `aud` of ID token | V10.5 |
| Consent screens | V10.7 |
| Crypto library choice, key size, constant-time comparison | V11.2 |
| Encryption algorithms and modes | V11.3 |
| Hashing, HMAC, password hashing (Argon2id/bcrypt) | V11.4 |
| Random tokens, ids, CSRF tokens (`secrets` vs `random`) | V11.5 |
| Signatures, asymmetric keys | V11.6 |
| TLS versions/ciphers | V12.1 |
| HTTPS for external services | V12.2 |
| TLS to DB/queues/internal APIs, certificate validation (`verify=False`) | V12.3 |
| Service accounts, least privilege DB role, outbound allowlist | V13.2 |
| Secrets storage, rotation, vaults | V13.3 |
| `/docs`, debug mode, `.git` exposure, directory listing, version disclosure | V13.4 |
| Data classification | V14.1 |
| Sensitive data in URLs, caches, trackers, minimal responses, retention | V14.2 |
| Browser storage, `Cache-Control: no-store`, `Clear-Site-Data` | V14.3 |
| Dependency remediation times, SBOM, risky components | V15.1 |
| Outdated components, dependency confusion, resource-heavy features | V15.2 |
| Mass assignment, minimal response fields, outbound redirects, client IP, type juggling, prototype pollution, parameter pollution | V15.3 |
| Race conditions, TOCTOU, locks | V15.4 |
| Log content and format, sensitive data in logs | V16.2 |
| Security events: auth, authz failures, bypass attempts | V16.3 |
| Log injection, log protection | V16.4 |
| Error responses, fail-closed, last-resort handler | V16.5 |

Documentation-only sections (`Vx.1` in most chapters) matter in requirements mode, rarely
in code review.

## Source and license

Section files from the [OWASP Agent Skills Project](https://github.com/eoftedal/owasp-agent-skills-project)
by Erlend Oftedal (`references/ASVS/`), as redistributed in the OWASP Secure Agent
Playbook. Content: **OWASP Application Security Verification Standard 5.0**, © OWASP
Foundation, licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Changes: sections V1.4, V10.4, V10.6 and V17.1–V17.3 removed; this index rewritten
(the upstream index labelled the chapters with ASVS 4.0 names). Files in this folder are
shared under the same license.
