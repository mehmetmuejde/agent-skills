# Idioms — ownership, types, iterators, naming

## Ownership and borrowing

| Parameter needs to … | Take | Example |
|---|---|---|
| read text | `&str` | `fn slugify(title: &str) -> String` |
| read a list | `&[T]` | `fn total(items: &[LineItem]) -> Money` |
| read a path | `&Path` or `impl AsRef<Path>` | `fn load(path: &Path)` |
| store the value | owned type, or `impl Into<String>` | `fn new(name: impl Into<String>) -> Self` |
| usually borrow, sometimes allocate | `Cow<'_, str>` | normalizing input that is mostly clean |
| mutate in place | `&mut T` | `fn apply(order: &mut Order, change: Change)` |

- Pass small `Copy` types (ids, numbers, small enums) by value.
- `.clone()` is fine for `Arc`, cheap handles (`PgPool`, `reqwest::Client`) and when you
  really need a second owner. It is not a fix for a borrow error — restructure (shorter
  borrows, split structs, return values instead of holding references).
- Return owned data from functions unless the borrow obviously lives as long as `self`.
- `Rc`/`RefCell` only for single-threaded graphs; `Arc<Mutex<_>>` only for real shared
  mutable state — prefer message passing or ownership by one task.
- Fallible cleanup goes into an explicit `close(self) -> Result<…>`; `Drop` is best effort
  and never blocks (`block_on` inside `Drop` deadlocks runtimes).

## Control flow

```rust
// Expected miss: early return with let-else
let Some(user) = repo.find(id).await? else {
    return Err(OrderError::UnknownUser(id));
};

// let-chains (edition 2024) instead of nested if-let
if let Some(limit) = config.limit
    && items.len() > limit
{
    return Err(OrderError::TooManyItems { limit });
}
```

- Lazy alternatives avoid wasted work: `ok_or_else`, `unwrap_or_else`, `map_or_else`,
  `unwrap_or_default`.
- `inspect_err(|e| …)` to observe an error without changing it; `map_err` to convert.
- `matches!` for boolean pattern checks; `assert_matches!` (stable since 1.96, import
  `use std::assert_matches;`) in tests instead of `assert!(matches!(…))`.

## Types

- **Newtypes for ids and validated values** — the compiler then stops you from passing an
  `OrderId` where a `UserId` is expected:

  ```rust
  #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
  #[serde(transparent)]
  pub struct OrderId(uuid::Uuid);

  /// Non-empty, at most 254 bytes, contains exactly one `@`.
  #[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
  #[serde(try_from = "String")]
  pub struct Email(String);

  impl TryFrom<String> for Email {
      type Error = InvalidEmail;

      fn try_from(value: String) -> Result<Self, Self::Error> {
          let ok = !value.is_empty() && value.len() <= 254 && value.matches('@').count() == 1;
          if ok {
              Ok(Self(value))
          } else {
              Err(InvalidEmail)
          }
      }
  }
  ```

  "Parse, don't validate": once you hold an `Email`, it is valid — no re-checks deeper in
  the code.
- **Enums instead of strings and bools**: `Status::Paid` instead of `"paid"`,
  `Visibility::Private` instead of `is_public: bool`. Function parameters never take a
  bare `bool` flag.
- **Type state** (`Connection<Disconnected>` → `Connection<Connected>` via
  `PhantomData`) only where misuse is costly and the states are few.
- `#[derive(Debug)]` on every public type; implement `Display` for anything shown to
  users. Types holding secrets get a handwritten `Debug` that redacts
  (`f.debug_struct("ApiClient").finish_non_exhaustive()`).
- `Deref` only for smart-pointer-like wrappers, never to fake inheritance.
- No trait bounds on struct definitions — put them on the `impl` blocks that need them.
- `#[must_use]` on builders and on functions whose result is easy to forget.

## Numbers

- `u32::try_from(len)?` instead of `len as u32` (silent truncation).
- Sizes and offsets from input: `checked_add`/`checked_mul` (→ error) or
  `saturating_*` (→ clamp), chosen deliberately.
- Floats: `f64::total_cmp` for sorting; never `==` on computed floats. Money is never a
  float — integer minor units or a decimal type.
- `NonZeroU32` & co. where zero is invalid.

## Iterators and collections

- Keep iterator chains lazy; `collect()` once at the end. `.any()`, `.all()`,
  `.count()`, `.find()` instead of collecting just to check.
- `for` loops are fine — and better — for side effects and early exits.
- `Vec::with_capacity(n)` when the size is known; `extend` instead of `push` in a loop.
- `HashMap::entry(key).or_insert_with(…)` instead of `contains_key` + `insert`.
- `get(i)` instead of `[i]` for indexes that come from outside.
- `BTreeMap`/`BTreeSet` when deterministic order matters (snapshots, output).
- `itertools` only if the project already uses it.

## Naming

| Kind | Convention |
|---|---|
| Crates | `kebab-case` in `Cargo.toml` (`shop-domain`), `snake_case` in code (`shop_domain`) |
| Modules, functions, variables | `snake_case` |
| Types, traits, enum variants | `UpperCamelCase`; acronyms as words: `HttpClient`, `UserId` |
| Constants, statics | `SCREAMING_SNAKE_CASE` |
| Conversions | `as_*` cheap borrow, `to_*` expensive/allocating, `into_*` consumes `self` |
| Getters | field name without `get_` (`order.total()`) |
| Predicates | `is_*`, `has_*`, `can_*` |
| Fallible constructors | `try_new`, `parse`, or `TryFrom`/`FromStr` |
| Iterators | `iter()`, `iter_mut()`, `into_iter()` |

## Traits and generics

- **Concrete types first, then generics, then `dyn`.** Generics give static dispatch and
  inlining; `dyn Trait` for heterogeneous collections, plugin lists, runtime choice or to
  cut compile time/binary size. `&dyn Trait` before `Box<dyn Trait>`.
- Associated types when there is one natural choice per implementor (`Iterator::Item`);
  generic parameters when a type can implement the trait several times.
- A trait needs a reason: a real second implementation (a fake in tests counts — see
  `architecture.md`) or a published extension point. No trait for a single type "just in
  case".
- Implement std traits where they fit: `From`/`TryFrom`, `FromStr`, `Display`,
  `Default`, `AsRef`, `IntoIterator` for collections.
- "dyn compatible" is the current term for what older docs call "object safe".

## API guideline basics (for any `pub` item)

- Public types implement `Debug`; `Clone`, `PartialEq`, `Eq`, `Hash`, `Default` where they
  make sense. Error types are `Send + Sync + 'static`.
- Constructors are `new`/`with_*`/builders; many optional fields → builder.
- Accept generic inputs (`impl AsRef<str>`), return concrete types.
- Keep fields private unless the type is plain data; accessors keep you free to change
  representation.
- Full rules for published crates: `library.md`.

## Macros

Functions and generics before macros. A `macro_rules!` macro is fine for repetitive
boilerplate inside one crate; use `$crate::` paths. Procedural macros live in their own
`*-macros` crate and report errors with spans (`syn::Error`), not panics.
