# Forms

The project uses **either** React Hook Form + Zod **or** TanStack Form + Zod — detect it
from `package.json` and existing forms, never mix both. A project without forms yet: ask
the user which one to use — don't decide alone. The rules in sections 1, 4 and 5
apply to both.

## 1. Rules for every form

- **One Zod schema per form**, in the `model` segment of the slice that owns the form.
  Types come from the schema (`z.input` / `z.output`), not from hand-written interfaces.
- Client validation is for the user's convenience; **the backend validates again** and
  is the authority. Server-side field errors are mapped back onto the fields.
- **Validation only through the schema** — no manual checks scattered across handlers
  (`if (email.includes('@'))`), no ad-hoc regexes next to it. The schema is defined once
  and its types are derived (`z.infer`/`z.input`/`z.output`) — no double maintenance.
- Schemas constrain everything: `max()` on strings, `int()`/`min()`/`max()` on numbers,
  `z.enum` instead of free text, `z.email()` / `z.url()` for formats.
- `defaultValues` for every field (controlled inputs never switch from `undefined` to a
  value).
- Submit is a real `<button type="submit">` inside a `<form>`; `Enter` submits.
- While submitting: disable the submit button (or ignore double submits) and show
  progress; on success give feedback (navigation, toast in a live region).
- Errors are never swallowed: network/server errors appear as a form-level message.
- Forms that write data call a TanStack Query mutation (`data-and-state.md`) — no
  `fetch` inside the submit handler.
- Unsaved changes on navigation: block with the router's blocker only where data loss
  hurts (long forms), not everywhere.

## 2. React Hook Form + Zod

```tsx
// features/edit-profile/model/profile.schema.ts
export const profileSchema = z.object({
  displayName: z.string().trim().min(2, { error: 'Enter at least 2 characters' }).max(50),
  email: z.email({ error: 'Enter a valid email address' }),
  age: z.coerce.number().int().min(18).max(130),
})
export type ProfileInput = z.input<typeof profileSchema>
export type ProfileOutput = z.output<typeof profileSchema>
```

```tsx
// features/edit-profile/ui/ProfileForm.tsx
export function ProfileForm({ initial }: { initial: ProfileInput }) {
  const updateProfile = useUpdateProfile()
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProfileInput, unknown, ProfileOutput>({
    resolver: zodResolver(profileSchema),
    defaultValues: initial,
  })

  const onSubmit = handleSubmit(async (values) => {
    try {
      await updateProfile.mutateAsync(values)
    } catch (error) {
      applyServerErrors(error, setError) // field errors + root.serverError
    }
  })

  return (
    <form onSubmit={onSubmit} noValidate>
      <TextField
        label="Display name"
        error={errors.displayName?.message}
        {...register('displayName')}
      />
      {errors.root?.serverError ? (
        <p role="alert">{errors.root.serverError.message}</p>
      ) : null}
      <button type="submit" disabled={isSubmitting}>Save</button>
    </form>
  )
}
```

- `zodResolver` from `@hookform/resolvers/zod` (supports Zod 4). Without generics,
  `useForm({ resolver: zodResolver(schema) })` infers input and output types. If you
  pass generics, pass all three (`useForm<Input, unknown, Output>`) — a single generic
  breaks inference for `coerce`/`default`/`transform`.
- Zod 4: customize messages with `{ error: '…' }` (`message` is deprecated); the input
  type of `z.coerce.*` is `unknown`, so `getValues('age')` is untyped — use the submit
  data, which has the output type.
- `register` for native inputs; `Controller`/`useController` only for components that
  can't take a ref (custom selects, date pickers).
- `noValidate` on the form: Zod messages replace the browser's validation bubbles.
- `shouldFocusError` (default `true`) moves focus to the first invalid field on submit —
  keep it, it is part of accessible error handling.
- Server errors: `setError('fieldName', { message })` for field errors,
  `setError('root.serverError', { message })` for form-level errors.
- Don't `watch()` the whole form at the top level (re-renders on every keystroke); use
  `useWatch({ name })` in the small component that needs the value.

## 3. TanStack Form + Zod

```tsx
export function ProfileForm({ initial }: { initial: ProfileInput }) {
  const updateProfile = useUpdateProfile()
  const form = useForm({
    defaultValues: initial,
    validators: { onSubmit: profileSchema },
    onSubmit: async ({ value }) => {
      await updateProfile.mutateAsync(profileSchema.parse(value))
    },
  })

  return (
    <form
      noValidate
      onSubmit={(event) => {
        event.preventDefault()
        void form.handleSubmit()
      }}
    >
      <form.Field name="displayName">
        {(field) => (
          <TextField
            label="Display name"
            name={field.name}
            value={field.state.value}
            onBlur={field.handleBlur}
            onChange={(event) => field.handleChange(event.target.value)}
            error={
              field.state.meta.isTouched && !field.state.meta.isValid
                ? field.state.meta.errors.map((issue) => issue?.message).join(', ')
                : undefined
            }
          />
        )}
      </form.Field>
      <form.Subscribe selector={(state) => state.isSubmitting}>
        {(isSubmitting) => <button type="submit" disabled={isSubmitting}>Save</button>}
      </form.Subscribe>
    </form>
  )
}
```

- Zod schemas are passed directly as validators (Standard Schema), at form or field
  level; no adapter package. With a schema, `field.state.meta.errors` holds issue
  objects — render `issue.message`.
- Schema validation does **not** transform the submitted value: `value` in `onSubmit` is
  the raw input. Parse it with the schema (as above) when the schema coerces, trims or
  sets defaults.
- Choose the validation timing deliberately: `onSubmit` first, then `onChange`/`onBlur`
  for fields that were touched — don't show errors while the user is still typing the
  first time.
- Subscribe narrowly with `form.Subscribe` or `useSelector(form.store, selector)`; don't
  read the whole form state at the top.
- For many forms with the same field components, build them once in `shared/ui/form`:
  `createFormHookContexts()` → `createFormHook({ fieldContext, formContext,
  fieldComponents, formComponents })` → `useAppForm` with `<form.AppField>`.

## 4. Accessible field markup

Every field component in `shared/ui` implements this once, so feature code can't get it
wrong:

```tsx
export function TextField({ label, error, description, id, ...input }: TextFieldProps) {
  const autoId = useId()
  const inputId = id ?? autoId
  const errorId = `${inputId}-error`
  const descriptionId = `${inputId}-description`
  const describedBy = [description ? descriptionId : null, error ? errorId : null]
    .filter(Boolean)
    .join(' ') || undefined

  return (
    <div>
      <label htmlFor={inputId}>{label}</label>
      {description ? <p id={descriptionId}>{description}</p> : null}
      <input id={inputId} aria-invalid={error ? true : undefined} aria-describedby={describedBy} {...input} />
      {error ? <p id={errorId}>{error}</p> : null}
    </div>
  )
}
```

- Visible `<label>` linked with `htmlFor`/`id` (`useId` for ids) [WCAG 1.3.1, 3.3.2].
- Invalid field: `aria-invalid="true"` and the error text linked via
  `aria-describedby` [WCAG 3.3.1].
- Required fields: the `required` attribute (or `aria-required`) plus a visible
  indicator explained once at the top of the form.
- Error text says what is wrong **and how to fix it** ("Enter a date after
  01.01.2024"), not just "Invalid" [WCAG 3.3.3].
- Errors are not shown by color alone (icon + text) [WCAG 1.4.1].
- On a failed submit, focus moves to the first invalid field; for long forms show an
  error summary at the top (`role="alert"`, links to the fields) and focus it.
- Groups of radios/checkboxes: `<fieldset>` + `<legend>`; the group error is linked to
  the fieldset.
- Correct `type` (`email`, `tel`, `url`, `number` only for real numbers) and
  `autoComplete` tokens [WCAG 1.3.5]; `inputMode` for numeric text fields (codes, IBAN).
- Don't disable paste in password/OTP fields [WCAG 3.3.8].

## 5. Testing forms

- Fill the form like a user: `user.type(screen.getByLabelText('Display name'), 'Ann')`,
  submit with `user.click(screen.getByRole('button', { name: 'Save' }))`.
- Assert visible error text and `aria-invalid`; assert focus moved to the first invalid
  field (`toHaveFocus()`).
- Test the server-error path (mock the API with an error response) and the double-submit
  guard.
- Unit-test complex schemas (cross-field rules, transforms) directly with
  `schema.safeParse`.
