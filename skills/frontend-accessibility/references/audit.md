# Accessibility audit / review

For reviewing existing UI or a diff. Read-only unless asked to fix; fixes are minimal and
targeted — no refactoring of unrelated code, no UI-library migration.

## Workflow

1. **Scope**: files/components/pages; which flows matter (login, checkout, main forms).
2. **Static pass over the code** — two walks:
   - *Keyboard walk*: can every flow complete without a mouse? Native elements, key
     handlers on custom widgets, focus management (dialogs, route changes), visible
     focus styles, no positive tabindex.
   - *Screen-reader walk*: does every control announce name, role, state? Labels,
     `alt`, `aria-*` correctness, live regions, headings/landmarks.
   - Plus: forms (labels, autocomplete, errors), contrast tokens, targets, motion guards,
     zoom/reflow risks. Use the "Before you finish" table in `SKILL.md` as grep list:

   ```sh
   rg -n '<(div|span)[^>]*onClick' src
   rg -n 'outline(-none|:\s*none)' src
   rg -n 'tabIndex=\{?[1-9]' src
   rg -n '<img(?![^>]*\balt=)' --pcre2 src
   rg -n 'maximum-scale=1|user-scalable=no' .
   rg -n 'onPaste' src
   rg -n 'transition:\s*all|transition-all' src
   ```

3. **Rendered pass** (if the app or Storybook runs): axe/Lighthouse, accessibility tree,
   keyboard through the flow. Checks that couldn't be run are listed as
   "Not verified".
4. **Verify** every finding at its location; group by root cause.

## Severity

| Severity | Meaning | Examples |
|---|---|---|
| **HIGH** | Prevents a task or hides content from assistive tech | missing accessible name, no keyboard path, keyboard trap, no visible focus, unlabeled field, meaning by color only, loss at 200 %/320 px, motion ignoring reduced motion |
| **MEDIUM** | Makes an interaction meaningfully harder | missing error linkage, no focus return after dialog, focus obscured, missing announcement, target below 24 px |
| **LOW** | Isolated polish | redundant ARIA, heading level skipped, non-specific link text in an otherwise clear context |

Only WCAG A/AA failures or blocked tasks can be HIGH; AAA and conventions are at most LOW.
Mapping to the code-review skill: HIGH → Blocker (task blocked) or Major, MEDIUM →
Major/Minor, LOW → Minor/Nit.

## Report

Written in the conversation language; the template below is the English version.

```markdown
## Accessibility-Review: <Scope>

**Verdict:** <Blocked | OK with open points | OK> — <one sentence>
**Checked:** static <yes> · rendered <yes/no> · keyboard <yes/no> · screen reader <yes/no>

1. **[HIGH] Icon buttons without an accessible name** — WCAG 4.1.2
   `src/features/cart/ui/CartItem.tsx:42`, `…/WishlistItem.tsx:31`
   Screen readers announce only "button"; users can't tell what gets removed.
   **Fix:** `aria-label={`Remove ${item.name}`}`, icon `aria-hidden="true"`.

### Not verified
- <checks that could not be run>
```

One finding per root cause with all locations; before/after only when the fix isn't
obvious. Nothing to report → "No accessibility findings" plus what was verified.
