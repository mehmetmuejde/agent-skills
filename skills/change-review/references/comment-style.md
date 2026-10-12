# Comment style — one line, typed by hand

Every finding gets a review comment that can be pasted or posted as is. It must read
like a colleague typed it quickly in the MR — not like a generated report.

## Language

- Write the comment in the **team's language** — by default the language of the
  conversation.
- On request, add the same comment in a **second language** (e.g. German and English);
  the user picks one when posting. Both versions follow the same rules — translate the
  thought, not the words.

## Rules

- **One line**, one sentence (two short ones at most). Aim for ≤ 120 characters.
- Say the problem and the fix, nothing else. The location is the line the comment sits
  on — don't repeat file names or line numbers.
- Plain words. No headings, no bold, no bullet lists, no emojis, no severity labels, no
  "Finding #3", no CWE/ASVS ids (those stay in the chat report).
- Direct: imperative or a short question. Match the team's register (e.g. German "du"
  vs. "Sie").
- Name the concrete thing: the function, the field, the hook — not "this code".
- Small stuff may start with `nit:`. Nothing else gets a prefix.
- A question when you're not sure; a statement when you are.
- Only lowercase start if it feels natural (`nit: …`); otherwise normal sentence case.
- Code identifiers in backticks are fine; code blocks are not.

### Avoid — sounds generated

| Don't | Do |
|---|---|
| "Consider refactoring this to improve maintainability." | "Pull this into `get_owned_order`, we already have it in `orders`." |
| "It might be beneficial to add error handling here." | "If `fetch_invoice` returns `None`, the next line blows up." |
| "This could potentially lead to a security vulnerability." | "Missing the owner filter, anyone can read other people's orders." |
| "Great job! Just one small suggestion: …" | "nit: `userData` → `user` is enough." |
| "I noticed that …", "Please note that …", "It's worth mentioning …" | straight to the point |
| em dashes, semicolons chaining three thoughts | one thought per comment |

## Examples

English, with German as an example second language:

| Finding | EN | DE |
|---|---|---|
| Missing ownership check | Missing the owner filter here, anyone can read other people's orders. | Hier fehlt der Owner-Filter, so kann jeder fremde Bestellungen abrufen. |
| Blocking call in async route | `requests.get` blocks the event loop here, use `httpx.AsyncClient` or make the route `def`. | `requests.get` blockiert hier den Event-Loop, nimm `httpx.AsyncClient` oder mach die Route `def`. |
| Duplicate helper | We already have this as `formatMoney` in `shared/lib`, let's use that. | Haben wir schon als `formatMoney` in `shared/lib`, bitte das nehmen. |
| Missing test | Can you add a test for the 404 case with someone else's order? | Kannst du noch einen Test für den 404-Fall bei fremden Orders ergänzen? |
| Derived state in effect | No need for the `useEffect`, just compute `total` during render. | Das `useEffect` brauchst du nicht, `total` kannst du direkt im Render berechnen. |
| Icon button without name | This button needs an `aria-label`, otherwise screen readers just say "button". | Der Button braucht ein `aria-label`, sonst liest der Screenreader nur „Schaltfläche“. |
| Breaking API change | Dropping `customer_name` breaks `OrderCard` in the frontend, it still reads it. | `customer_name` fällt raus, das Frontend nutzt das noch in `OrderCard`. |
| Migration risk | `NOT NULL` without a default will fail on prod, the table isn't empty. | Das `NOT NULL` ohne Default schlägt auf Prod fehl, da gibt's schon Zeilen. |
| Missing translation | `orders.empty` is only in `en.json`, the German file is missing it. | `orders.empty` gibt's nur in `en.json`, in der deutschen Datei fehlt es. |
| Naming nit | nit: `data2` doesn't say much, maybe `pendingInvoices`? | nit: `data2` sagt nix, vielleicht `pendingInvoices`? |
| Question | Is this meant to be reachable without login? | Soll das wirklich ohne Login erreichbar sein? |

## Summary comment

One to three short sentences, same tone, in the chosen language:

- EN: "Looks good, two things left: the owner filter in `orders` and a test for the 404
  case. The rest is minor."
- DE: "Sieht gut aus, zwei Sachen noch: der Owner-Filter in `orders` und ein Test für den
  404-Fall. Rest sind Kleinigkeiten."

No praise padding, no lists, no counts by severity.

## In the chat report

Each finding in the report ends with its one-liner — one line per language:

```markdown
   💬 Missing the owner filter here, anyone can read other people's orders.
```

With a second language requested, prefix each line with the language code:

```markdown
   💬 EN: Missing the owner filter here, anyone can read other people's orders.
   💬 DE: Hier fehlt der Owner-Filter, so kann jeder fremde Bestellungen abrufen.
```

(The 💬 marker and the language code are only for the chat report — never part of the
posted comment.)
