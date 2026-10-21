# Testing — pytest

Tests are written together with the change, not afterwards. CI enforces **80 % line and
branch coverage**; below that the pipeline fails.

## Tooling

```bash
uv add --dev pytest pytest-cov pytest-mock respx
```

| Package | Purpose |
|---|---|
| `pytest`, `pytest-cov` | runner, coverage |
| `pytest-mock` | `mocker` fixture for internal functions |
| `respx` | mocks outbound HTTPX calls |
| `httpx` | `TestClient` / `AsyncClient` (comes with `fastapi[standard]`) |

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --cov=app --cov-branch --cov-report=term-missing"

[tool.coverage.run]
omit = ["app/db/migrations/*"]

[tool.coverage.report]
fail_under = 80
skip_covered = true
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError"]
```

`uv run pytest` runs everything. Coverage is a floor, not the goal: a test that asserts
nothing is worse than a missing test.

## What to test where

| Level | Tests | Tools |
|---|---|---|
| Service (unit) | business rules, edge cases, domain exceptions | service built by hand with an in-memory repository |
| Repository | queries, scoping by owner/tenant | real database, rolled-back session |
| API (integration) | status codes, validation (422), auth (401/403/404), response shape | `TestClient` + `dependency_overrides` |
| Database | queries, constraints, migrations, **RLS isolation** | real PostgreSQL |

Services are pure (no FastAPI imports) and get their repository injected, so they are
tested directly — no HTTP and no database needed:

```python
class InMemoryOrderRepository(OrderRepository):
    def __init__(self) -> None:
        self.orders: list[Order] = []

    def add(self, order: Order) -> None:
        self.orders.append(order)


def test_create_sets_owner_from_user(user: User) -> None:
    repository = InMemoryOrderRepository()
    service = OrderService(create_autospec(Session, instance=True), repository)

    service.create(OrderCreate(item="book"), owner=user)

    assert repository.orders[0].owner_id == user.id
```

To test the router without the database, override the service dependency:

```python
app.dependency_overrides[get_order_service] = lambda: OrderService(fake_session, repository)
```

## Test client and dependencies

```python
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:  # context manager: lifespan startup/shutdown run
        yield client
    app.dependency_overrides.clear()
```

- **Always a fixture** — never a module-level `client = TestClient(app)`.
- **Always clear `dependency_overrides`** after the `yield` — otherwise overrides bleed
  into other tests and cause flaky failures.
- `dependency_overrides` is the tool for swapping FastAPI dependencies — never
  `unittest.mock.patch` on a dependency.
- Override auth with a fixture that returns a specific user and test as **anonymous,
  owner, other user and admin** — e.g. fixtures `client`, `client_user`,
  `client_other_user`, `client_admin`:

  ```python
  @pytest.fixture
  def client_user(client: TestClient, user: User) -> TestClient:
      app.dependency_overrides[get_current_user] = lambda: user
      return client
  ```

- `TestClient` covers the vast majority of tests — sync tests work with async
  endpoints. Use `httpx.AsyncClient` with `@pytest.mark.anyio` only when the test itself
  must `await` (e.g. it holds an async DB session or awaits real async operations):

  ```python
  @pytest.fixture
  async def async_client() -> AsyncIterator[httpx.AsyncClient]:
      transport = httpx.ASGITransport(app=app)
      async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
          yield ac
  ```

## Fixture scopes

`scope="function"` (default) is the safe choice. `scope="session"` only for expensive,
stateless setup — engine creation, running migrations. Stateful resources (sessions,
clients, overrides) never get a broad scope, otherwise data leaks between tests.

## Database in tests

- Use a **real PostgreSQL** — never SQLite as a stand-in; RLS, JSONB, constraints and
  locking behave differently. Either the local Compose database (separate test DB) or a
  throwaway container via testcontainers — decided per project.
- **Never** test against a production database.
- Run migrations once per session (`alembic upgrade head`) so tests cover them.
- Isolate tests: each test runs in a transaction that is rolled back (or truncate per
  test). Tests must not depend on order. Rollback is fast and needs no wipe:

  ```python
  @pytest.fixture
  def session(engine: Engine) -> Iterator[Session]:
      with engine.connect() as connection:
          transaction = connection.begin()
          # commits inside the code under test only release a savepoint
          session = Session(bind=connection, join_transaction_mode="create_savepoint")
          try:
              yield session
          finally:
              session.close()
              transaction.rollback()
  ```

- Build data with small factory functions/fixtures, not shared global fixtures that every
  test mutates.

## Security tests are mandatory

For every endpoint that touches user-owned data:

- unauthenticated → 401,
- other user's object → 404 (BOLA),
- missing permission → 403 (BFLA),
- unknown/forbidden fields in the body → 422 (mass assignment),
- response doesn't contain internal fields — assert explicitly that `password_hash`,
  tokens etc. are **absent**,
- for RLS tables: a query as tenant A returns none of tenant B's rows, even without the
  `WHERE` filter.

Negative tests for validation: too long strings, out-of-range numbers, wrong enum values,
tampered/expired tokens. Use `parametrize` for the variants:

```python
@pytest.mark.parametrize(
    "payload",
    [
        {"email": ""},
        {"email": "no-at-sign"},
        {},
        {"email": "valid@example.com", "password": "short"},
        {"email": "valid@example.com", "password": "long-enough-1", "is_admin": True},
    ],
)
def test_create_user_rejects_invalid_payload(client: TestClient, payload: dict) -> None:
    response = client.post("/users", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("token", ["", "invalid", "expired-token-fixture"])
def test_me_rejects_bad_tokens(client: TestClient, token: str) -> None:
    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
```

## What every API test checks

- The **status code**, explicitly.
- The **response body** — structure and values, not just the status.
- The **database state** after mutations.

## Mocking

| What | Tool |
|---|---|
| FastAPI dependency | `app.dependency_overrides` |
| Internal function / service | `mocker.patch` (pytest-mock) |
| Async function | `mocker.patch(..., new_callable=AsyncMock)` |
| Outbound HTTPX call | `respx` (or `httpx.MockTransport` on an injected client) |
| Outbound `requests` call (legacy code) | `responses` |

- **Patch where the name is looked up, not where it is defined**:
  `mocker.patch("app.features.users.service.send_email")` ✅ —
  `mocker.patch("app.shared.email.send_email")` ❌ (the service already imported it).
- Async functions need `AsyncMock`; a plain mock causes "coroutine was never awaited".
- No network calls to real third-party services — tests run offline. Test the error
  paths of upstream services too:

```python
@respx.mock
def test_profile_returns_502_when_upstream_fails(client_user: TestClient) -> None:
    respx.get("https://api.example.com/profiles/1").mock(
        return_value=httpx.Response(503, json={"error": "unavailable"})
    )
    response = client_user.get("/profiles/1")
    assert response.status_code == 502
```

## Background tasks, WebSockets, lifespan

- **Background tasks** run synchronously in `TestClient` after the response — mock the
  task function and assert the call:

  ```python
  def test_signup_sends_welcome_email(client: TestClient, mocker: MockerFixture) -> None:
      send = mocker.patch("app.features.users.router.send_welcome_email")
      response = client.post(
          "/users", json={"email": "new@example.com", "password": "long-enough-1"}
      )
      assert response.status_code == 201
      send.assert_called_once_with("new@example.com")
  ```

- **WebSockets**: `with client.websocket_connect("/ws") as ws:` then
  `ws.send_text(...)` / `ws.receive_text()`.
- **Lifespan**: startup and shutdown only run when `TestClient` is used as a context
  manager (as in the `client` fixture).

## Rules

- Test names describe behavior: `test_returns_404_for_order_of_other_user`.
- Arrange / act / assert, one behavior per test.
- Time and randomness are injected or frozen, never real sleeps.
- A bug fix starts with a failing test that reproduces it.

## Anti-patterns

- ❌ Module-level `TestClient(app)` instead of a fixture with `yield`.
- ❌ Not clearing `dependency_overrides` → bleeding between tests, flaky.
- ❌ `unittest.mock.patch` for FastAPI dependencies instead of `dependency_overrides`.
- ❌ Calling real external APIs.
- ❌ Testing against a production database.
- ❌ Checking only the status code, not the body.
- ❌ Not asserting that sensitive fields are absent from responses.
- ❌ `requests` instead of `httpx` — `TestClient`/`AsyncClient` are HTTPX-based.
- ❌ Forgetting `AsyncMock` for async functions.
- ❌ Fixtures with too broad a scope for stateful resources.
- ❌ Tests that depend on each other or on execution order.
