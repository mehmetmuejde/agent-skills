# Dependency injection

Use a dependency when the logic:

- can't be expressed as Pydantic validation and needs extra logic,
- depends on external resources or could block,
- is needed by other dependencies (sub-dependency),
- is shared by several endpoints — fail early, authenticate, authorize,
- needs cleanup (DB session, file handle) → dependency with `yield`,
- needs request data (headers, cookies, query parameters).

## Annotated + type alias

Every reusable dependency gets an alias next to its definition:

```python
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
```

## `yield` and `scope`

Exit code of a `yield` dependency runs:

- `scope="request"` (default) — after the response has been sent.
- `scope="function"` — after the response data is produced, **before** it is sent.
  Use it when the cleanup must finish before the client sees the result (e.g. a commit
  the client relies on).

```python
UserNameDep = Annotated[str, Depends(get_username, scope="function")]
```

Always wrap the `yield` in `try/finally` (or a `with` block) so cleanup runs on errors.
Don't swallow exceptions in a `yield` dependency — re-raise after cleanup.

## No class dependencies

Don't use `Depends()` on a class. Write a function that returns the instance:

```python
@dataclass
class Paginator:
    offset: int
    limit: int


def get_paginator(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Paginator:
    return Paginator(offset=offset, limit=limit)


PaginatorDep = Annotated[Paginator, Depends(get_paginator)]
```

## Layered wiring: session → repository → service

Each feature's `dependencies.py` builds its layers with provider functions — one per
layer, each with an alias. Services and repositories stay free of FastAPI imports:

```python
# features/orders/repository.py
class OrderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_owned(self, order_id: UUID, owner_id: UUID) -> Order | None:
        return self._session.scalar(
            select(Order).where(Order.id == order_id, Order.owner_id == owner_id)
        )

    def add(self, order: Order) -> None:
        self._session.add(order)


# features/orders/service.py
class OrderService:
    def __init__(self, session: Session, repository: OrderRepository) -> None:
        self._session = session
        self._repository = repository

    def create(self, data: OrderCreate, owner: User) -> Order:
        order = Order(**data.model_dump(), owner_id=owner.id)  # owner from the server
        self._repository.add(order)
        self._session.commit()  # the service owns the transaction
        return order


# features/orders/dependencies.py
def get_order_repository(session: SessionDep) -> OrderRepository:
    return OrderRepository(session)


OrderRepositoryDep = Annotated[OrderRepository, Depends(get_order_repository)]


def get_order_service(session: SessionDep, repository: OrderRepositoryDep) -> OrderService:
    return OrderService(session, repository)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


# features/orders/router.py
@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate, service: OrderServiceDep, user: CurrentUserDep
) -> OrderPublic:
    return OrderPublic.model_validate(service.create(data, owner=user))
```

- FastAPI caches a dependency **once per request**: `get_session` runs once, so service
  and repository share one session and one transaction.
- Providers are plain `def` when the data path is sync, `async def` only with an async
  session.
- Tests swap a whole layer with `app.dependency_overrides[get_order_service] = ...` or
  build the service by hand with a fake repository (`references/testing.md`).

## Router-level dependencies

Shared dependencies go on the router — auth, permission checks, CSRF checks:

```python
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("admin"))],
)
```

## Authorization as dependencies

Authorization is enforced on the server, in dependencies or the service layer — never
only in the frontend (ASVS 8.3.1).

- **Function level (BFLA, API5)** — who may call this operation at all: a permission
  dependency per router or operation. Deny by default; admin routers are separate
  routers with their own dependency.
- **Object level (BOLA, API1)** — may this user touch *this* object: a dependency or
  service function that loads the object **scoped by owner/tenant** and raises 404
  otherwise.
- **Property level (BOPLA, API3)** — which fields may be read/written: separate input and
  output schemas per role/action.

```python
def require_role(*roles: Role) -> Callable[[User], User]:
    def checker(user: CurrentUserDep) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        return user

    return checker


def get_owned_order(
    order_id: Annotated[UUID, Path()],
    user: CurrentUserDep,
    session: SessionDep,
) -> Order:
    order = session.scalar(
        select(Order).where(Order.id == order_id, Order.owner_id == user.id)
    )
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


OwnedOrderDep = Annotated[Order, Depends(get_owned_order)]
```

Log denied authorization decisions (see `observability.md`).

## Testing

Swap dependencies in tests with `app.dependency_overrides[get_session] = fake_session`
and reset them afterwards. Keep business logic in plain functions that receive their
dependencies as arguments, so they are testable without FastAPI.
