# Authentication

Three models are in use. Find out which one the project uses before changing auth code;
a project can combine them (e.g. cookie session for the SPA, bearer tokens for API
clients).

| Model | Typical use |
|---|---|
| Cookie session + CSRF | Own SPA on the same site as the API |
| Bearer JWT (own issuer) | API clients, service-to-service, mobile |
| External IdP (OIDC) | Keycloak, Entra ID, Auth0 … — the API validates their tokens |

## General rules

- Authentication is a dependency (`CurrentUserDep`), applied at router level.
  Endpoints are protected by default; public ones are explicit.
- Identify the user by a stable id, never by email or display name. With OIDC: the pair
  `iss` + `sub` (ASVS 10.3.3).
- Authorization decisions use server-side data, not claims the client controls.
- Auth failures return 401 with a generic message ("Invalid credentials") — no hint
  whether the user exists.
- Rate-limit login, registration, password reset, OTP and token endpoints per account
  **and** per client IP (ASVS 2.4.1, API2/API4). Prefer the reverse proxy / gateway;
  use a limiter library in the app only when the proxy can't do it (e.g. per-account
  limits that need the authenticated user).
- Log logins, failures, logouts, password changes and denied access as audit events
  (see `observability.md`), never with passwords or tokens.

## Bearer JWT (own issuer)

Decode with an explicit algorithm allowlist, audience, issuer and required claims
(ASVS 9.1, 9.2):

```python
import jwt  # PyJWT

payload = jwt.decode(
    token,
    key=settings.jwt_public_key,
    algorithms=["RS256"],          # allowlist; never from the token header, never "none"
    audience=settings.jwt_audience,
    issuer=settings.jwt_issuer,
    options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    leeway=30,
)
if payload.get("typ") != "access":  # refresh tokens are not access tokens (ASVS 9.2.2)
    raise credentials_error
```

- Short-lived access tokens (minutes); refresh tokens are long-lived, rotated on use and
  revocable server-side.
- Don't put secrets or personal data beyond the id into the payload — it is only
  base64, not encrypted.
- Key material comes from configuration. Ignore/allowlist `jku`, `x5u`, `jwk` headers
  (ASVS 9.1.3).
- Logout and "log out everywhere" need server-side revocation (denylist by `jti` or a
  per-user token version) — a JWT stays valid until `exp` otherwise (ASVS 7.4.1).

## External IdP (OIDC)

The API is a resource server. It validates access tokens issued by the IdP:

```python
jwks_client = jwt.PyJWKClient(settings.oidc_jwks_url, cache_keys=True)


def verify_access_token(token: str) -> dict[str, Any]:
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience=settings.oidc_audience,
        issuer=settings.oidc_issuer,      # exact match incl. trailing slash
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )
```

- JWKS URL and issuer come from configuration (or the IdP's discovery document fetched
  once at startup), never from the token.
- Accept **access tokens only**. An ID token is proof of login for the client, not an
  API credential (ASVS 9.2.2).
- Check `aud` against this API (ASVS 10.3.1); use `scope`/roles claims for authorization
  through an explicit mapping (IdP role → app permission) (ASVS 10.3.2).
- Local user records are linked by `iss` + `sub` (just-in-time provisioning), not by
  email.
- If the backend runs the browser login itself (backend-for-frontend): Authorization
  Code flow with PKCE, `state` and `nonce`, exact `redirect_uri` match; the backend keeps
  the tokens and gives the browser a session cookie (→ cookie model below).

## Cookie session + CSRF

### Cookie

```python
response.set_cookie(
    "__Host-session",
    session_id,
    httponly=True,      # not readable by JS (ASVS 3.3.4)
    secure=True,        # HTTPS only (ASVS 3.3.1)
    samesite="lax",     # "strict" if no cross-site navigation into the app is needed
    path="/",           # __Host- requires Path=/ and no Domain (ASVS 3.3.3)
    max_age=...,
)
```

- Opaque random session id (`secrets.token_urlsafe(32)`), session data on the server.
- New session id on login and re-authentication; the old one is invalidated
  (ASVS 7.2.4).
- Logout deletes the session server-side, not only the cookie (ASVS 7.4.1).
- Disabling/deleting a user kills all their sessions; after a password or MFA change
  offer "log out other sessions" (ASVS 7.4.2, 7.4.3).

### CSRF

`SameSite` alone is not enough (same-site subdomains, older browsers, top-level GET).
For every state-changing request (`POST`, `PUT`, `PATCH`, `DELETE`) — as a router-level
dependency (ASVS 3.5.1–3.5.3):

1. **Check `Origin`** (fall back to `Referer`) against the allowlist of frontend origins;
   reject if missing or foreign. Alternatively/additionally reject
   `Sec-Fetch-Site: cross-site`.
2. **Plus one of:**
   - a required custom header (e.g. `X-CSRF-Token` with a double-submit value, or a
     fixed `X-Requested-With`) — a custom header forces a CORS preflight, which the
     strict CORS allowlist rejects, **or**
   - a synchronizer token stored in the session and compared with
     `secrets.compare_digest`.
3. Accept only `application/json` bodies on JSON endpoints — form content types don't
   trigger a preflight.
4. Never change state on `GET`.

CORS for the cookie model: explicit origins, `allow_credentials=True`, never `"*"`.

## Passwords (only if the app stores them)

- Hash with Argon2id (or bcrypt for existing data) via a maintained library; never
  plain SHA/MD5 (ASVS 11.4.2). Upgrade hashes on login when parameters change.
- Policy (ASVS 6.2): min 8 characters (15 recommended), allow at least 64, **no
  composition rules**, no truncation or case changes, check against a list of common/
  breached passwords, no forced periodic rotation.
- Password change requires the current password (ASVS 6.2.3).
- Reset tokens: random, single-use, short expiry, stored hashed; the response is the same
  whether the email exists or not.
- Compare secrets with `secrets.compare_digest` / `hmac.compare_digest`, never `==`.
