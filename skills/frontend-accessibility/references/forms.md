# Forms

Applies to React Hook Form and TanStack Form alike — the library manages state, the
markup must still carry labels, descriptions and errors.

## Labels [1.3.1, 3.3.2]

- Every input, select, textarea: `<label htmlFor>` → `id`, or a wrapping `<label>`.
- A placeholder is never a label (vanishes on typing, usually fails contrast).
  Placeholders show an example pattern and end with `…`.
- Checkbox/radio and its text share one hit target — no dead zone.
- Required: native `required` + a visible marker explained once ("* Pflichtfeld").
- Helper text linked via `aria-describedby`.
- Related fields grouped in `<fieldset>` + `<legend>` (address, radio groups).

## Autocomplete and input types [1.3.5]

| Field | `autoComplete` |
|---|---|
| Name | `name` / `given-name` / `family-name` |
| Email | `email` |
| Phone | `tel` |
| Address | `street-address`, `address-line1`, `postal-code`, `country` |
| Login | `username`, `current-password` |
| Sign-up / reset | `username`, `new-password` |
| 2FA code | `one-time-code` |
| Card | `cc-number`, `cc-exp`, `cc-csc`, `cc-name` |

Section prefixes where relevant: `autoComplete="shipping street-address"`.
`autoComplete="off"` on non-auth fields that would trigger password managers.

| Input | Use |
|---|---|
| Email, URL, phone | `type="email"`, `"url"`, `"tel"` |
| OTP, PIN, card number | `type="text" inputMode="numeric"` |
| Money, decimals | `type="text" inputMode="decimal"` |
| Real quantity | `type="number"` |

`spellCheck={false}` on emails, codes, usernames. Never block paste [3.3.8].

## Errors [3.3.1, 3.3.3]

```tsx
<label htmlFor="email">E-Mail</label>
<input
  id="email"
  type="email"
  autoComplete="email"
  aria-invalid={errors.email ? true : undefined}
  aria-describedby={errors.email ? 'email-error' : 'email-hint'}
  {...register('email')}
/>
<p id="email-hint">We will send you a confirmation.</p>
{errors.email && <p id="email-error">{errors.email.message}</p>}
```

- `aria-invalid="true"` only while invalid.
- Error inline next to the field, text + icon — never a red border alone [1.4.1].
- Error text says how to fix it ("Enter an email address like name@example.com"), not
  just "Invalid".
- On submit, focus the first invalid field (`setFocus` / `shouldFocusError` in RHF,
  field ref in TanStack Form). For long forms add an error summary at the top with links
  to the fields.
- Don't validate on every keystroke with announcements; validate on blur/submit.
- Accept free text and validate after — don't filter characters while typing. Trim
  before validating.

## Submit behavior

- Submit stays enabled until the request starts — no `disabled={!isValid}`.
- While pending: spinner **next to** the label ("Speichern …"), `aria-disabled="true"`,
  ignore repeated clicks in the handler. Native `disabled` on the focused button drops
  focus to `<body>`.
- Success → polite `role="status"` message; failure → focus the first invalid field or a
  form-level `role="alert"`.
- Warn before leaving with unsaved changes (router blocker / `beforeunload`).
- A re-render must never reset a typed value or move focus out of the field.

## Authentication [3.3.7, 3.3.8]

- No cognitive tests without alternative: allow paste and password managers, offer
  passkey/SSO/email link where possible.
- Don't ask again for data entered earlier in the same flow ("Shipping address same as
  billing address").
- Session timeouts warn and allow extending [2.2.1].

## Destructive actions [3.3.4]

Confirmation dialog or undo window — never immediate. Confirmation focus starts on the
safe option.
