# Web backends — axum 0.8 (primary), actix-web 4

The framework is chosen **per project**; detect it from `Cargo.toml` and never add the
other one. Examples use axum 0.8 + tower-http 0.7; the actix-web mapping is at the end.
Structure (feature slices, ports, composition root): `architecture.md`.

## Dependencies (axum)

```toml
[dependencies]
axum = { version = "0.8", features = ["macros"] }
tokio = { version = "1", features = ["rt-multi-thread", "macros", "net", "signal", "time"] }
tower = "0.5"
tower-http = { version = "0.7", features = [
    "trace", "timeout", "limit", "cors", "catch-panic", "request-id",
    "sensitive-headers", "set-header",
] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2"
tracing = "0.1"
uuid = { version = "1", features = ["v4", "serde"] }
```

## Routing — one router per feature

```rust
// orders/http.rs
pub fn router<R: OrderRepository, C: Clock>(service: Arc<OrderService<R, C>>) -> Router {
    Router::new()
        .route("/orders", get(list::<R, C>).post(create::<R, C>))
        .route("/orders/{id}", get(get_one::<R, C>).delete(cancel::<R, C>))
        .with_state(service)
}
```

- **Path parameters use `{id}`** (axum 0.8); `{*rest}` for wildcards. The old `:id` /
  `*rest` syntax panics at startup in 0.8.
- Each feature router owns its state and returns `Router` (state already applied); the
  app merges them. Generic handlers are instantiated in the router (`get_one::<R, C>`), so
  tests can mount the same router with fakes.
- Explicit method routing (`get`, `post`, …) — never one handler that branches on the
  method. State-changing operations never use `GET`.
- A JSON `fallback` for unknown routes so clients always get the same error shape.

## App assembly, middleware, serving

```rust
// http.rs
pub fn app(api: Router, health: Router, auth: AuthState, config: &HttpConfig) -> Router {
    let api = api
        // Protected by default: every API route requires a principal
        .route_layer(middleware::from_fn_with_state(auth, require_auth))
        .layer(DefaultBodyLimit::max(config.max_body_bytes));

    Router::new()
        .nest("/api/v1", api)
        .merge(health)                                    // /healthz/* outside /api
        .fallback(not_found)
        .layer(
            ServiceBuilder::new()                         // top runs first on the request
                .layer(SetSensitiveRequestHeadersLayer::new([
                    AUTHORIZATION,
                    COOKIE,
                ]))
                .layer(SetRequestIdLayer::x_request_id(MakeRequestUuid))
                .layer(TraceLayer::new_for_http())
                .layer(PropagateRequestIdLayer::x_request_id())
                .layer(CatchPanicLayer::new())
                .layer(TimeoutLayer::with_status_code(
                    StatusCode::SERVICE_UNAVAILABLE,
                    config.request_timeout,
                ))
                .layer(RequestBodyLimitLayer::new(config.max_body_bytes))
                .layer(cors(&config.allowed_origins)),
        )
}

fn cors(origins: &[HeaderValue]) -> CorsLayer {
    CorsLayer::new()
        .allow_origin(origins.to_vec())
        .allow_methods([Method::GET, Method::POST, Method::DELETE])
        .allow_headers([AUTHORIZATION, CONTENT_TYPE])
        .allow_credentials(true)
}

pub async fn serve(app: Router, addr: SocketAddr) -> std::io::Result<()> {
    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!(%addr, "listening");
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await
}

async fn shutdown_signal() {
    let ctrl_c = async {
        if let Err(err) = tokio::signal::ctrl_c().await {
            tracing::error!(%err, "cannot listen for Ctrl-C");
            std::future::pending::<()>().await;
        }
    };
    #[cfg(unix)]
    let terminate = async {
        match tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate()) {
            Ok(mut sigterm) => {
                sigterm.recv().await;
            }
            Err(err) => {
                tracing::error!(%err, "cannot listen for SIGTERM");
                std::future::pending::<()>().await;
            }
        }
    };
    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        () = ctrl_c => {},
        () = terminate => {},
    }
    tracing::info!("shutdown signal received");
}
```

- **Layer order**: `Router::layer` calls wrap from the outside — the **last** `.layer()`
  added runs **first**. Inside a `ServiceBuilder` the order is top to bottom. Put
  everything in one `ServiceBuilder` to keep it readable.
- `route_layer` applies only to matched routes: unknown paths return 404, not 401.
- **Timeout**: `TimeoutLayer::new` is deprecated since tower-http 0.6.7 — use
  `with_status_code`. For slow-loris style uploads add `RequestBodyTimeoutLayer` (idle) or
  `RequestBodyDeadlineLayer` (total, tower-http 0.7).
- **Body size** twice: `DefaultBodyLimit` (axum extractors, default 2 MB) and
  `RequestBodyLimitLayer` (whole body, also streaming). Set both explicitly.
- **CORS**: explicit origin list from config; never `CorsLayer::permissive()` or
  `Any` together with credentials. CORS is not access control.
- **Graceful shutdown** waits for in-flight requests; the timeout layer bounds that.
  Long-lived connections (SSE, WebSocket) need their own cancellation
  (`CancellationToken`, `async.md`). Kubernetes: shutdown must finish inside
  `terminationGracePeriodSeconds`.
- **Health**: `/healthz/live` (process only) and `/healthz/ready` (DB reachable), outside
  `/api` — same convention as the `docker-kubernetes` skill.
- **Rate limiting** at the reverse proxy / gateway; only without one, in the app
  (`tower_governor`). Login and expensive endpoints always have a limit.
- Behind a proxy, client IP and scheme come from `X-Forwarded-*` only if the proxy is
  trusted; otherwise use the socket address (`ConnectInfo`).

## Handlers and extractors

```rust
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CreateOrderRequest {
    items: Vec<OrderLineRequest>,
}

async fn create<R: OrderRepository, C: Clock>(
    State(service): State<Arc<OrderService<R, C>>>,
    user: CurrentUser,
    AppJson(body): AppJson<CreateOrderRequest>,      // body extractor last
) -> Result<(StatusCode, Json<OrderResponse>), ApiError> {
    let draft = body.try_into_draft()?;              // DTO → validated domain type
    let order = service.place(user.id, draft).await?;
    Ok((StatusCode::CREATED, Json(OrderResponse::from(&order))))
}
```

- **The body-consuming extractor (`Json`, `Form`, `Bytes`, `String`, `Multipart`) is the
  last argument** — otherwise it doesn't compile. `#[axum::debug_handler]` (feature
  `macros`) turns cryptic handler errors into readable ones.
- `Path<OrderId>` deserializes straight into the newtype; `Query<ListParams>` with
  `#[serde(default)]` and an upper bound on `limit`.
- `Option<T>` as an extractor requires `OptionalFromRequestParts` /
  `OptionalFromRequest` in 0.8 — implemented for `Path`, `Extension`, `MatchedPath`,
  `Json` and `Multipart`, **not** for `Query` (make the fields of the query struct
  optional instead). A missing value gives `None`, a malformed one still rejects.
- **Request DTOs** live in the feature's `http.rs`, use `deny_unknown_fields` (mass
  assignment) and convert into domain types with `TryFrom`; **response DTOs** list only
  the fields the client may see. Never serialize domain or row types directly.
- Return `Result<impl IntoResponse, ApiError>`; set `StatusCode::CREATED` /
  `NO_CONTENT` explicitly.

### JSON rejections in your own error shape

```rust
#[derive(Debug, FromRequest)]
#[from_request(via(axum::Json), rejection(ApiError))]
pub struct AppJson<T>(pub T);

impl From<JsonRejection> for ApiError {
    fn from(rejection: JsonRejection) -> Self {
        Self::BadRequest(rejection.body_text())
    }
}
```

## Errors → HTTP

```rust
#[derive(Debug, thiserror::Error)]
pub enum ApiError {
    #[error("bad request: {0}")]
    BadRequest(String),
    #[error("unauthenticated")]
    Unauthenticated,
    #[error("forbidden")]
    Forbidden,
    #[error("not found")]
    NotFound,
    #[error("conflict: {0}")]
    Conflict(&'static str),
    #[error("internal error")]
    Internal(#[source] Box<dyn std::error::Error + Send + Sync>),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            Self::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            Self::Unauthenticated => (StatusCode::UNAUTHORIZED, "unauthenticated".to_owned()),
            Self::Forbidden => (StatusCode::FORBIDDEN, "forbidden".to_owned()),
            Self::NotFound => (StatusCode::NOT_FOUND, "not found".to_owned()),
            Self::Conflict(msg) => (StatusCode::CONFLICT, (*msg).to_owned()),
            Self::Internal(err) => {
                tracing::error!(error = &**err as &dyn std::error::Error, "internal error");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    "internal error".to_owned(),
                )
            }
        };
        (status, Json(serde_json::json!({ "error": message }))).into_response()
    }
}

impl From<GetOrderError> for ApiError {
    fn from(err: GetOrderError) -> Self {
        match err {
            GetOrderError::NotFound(_) => Self::NotFound,
            GetOrderError::Store(e) => Self::Internal(Box::new(e)),
        }
    }
}
```

- One explicit `From<DomainError> for ApiError` per feature error — exhaustive, no `_`.
- Internal details (SQL errors, file paths, stack traces) are logged, never returned.
- "Not found" and "not yours" both return 404.
- `anyhow::Error` may appear inside `Internal` in the binary crate, never in domain code.

## Authentication — principal from middleware

```rust
#[derive(Debug, Clone)]
pub struct CurrentUser {
    pub id: UserId,
    pub tenant: TenantId,
}

pub async fn require_auth(
    State(auth): State<AuthState>,
    mut req: Request,
    next: Next,
) -> Result<Response, ApiError> {
    let token = req
        .headers()
        .get(AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
        .ok_or(ApiError::Unauthenticated)?;
    let user = auth
        .verifier
        .verify(token)
        .await
        .map_err(|_| ApiError::Unauthenticated)?;
    req.extensions_mut().insert(user);
    Ok(next.run(req).await)
}

impl<S: Send + Sync> FromRequestParts<S> for CurrentUser {
    type Rejection = ApiError;

    async fn from_request_parts(parts: &mut Parts, _state: &S) -> Result<Self, Self::Rejection> {
        parts
            .extensions
            .get::<CurrentUser>()
            .cloned()
            .ok_or(ApiError::Unauthenticated)
    }
}
```

- Custom extractors use native `async fn` — axum 0.8 dropped `#[async_trait]` for
  `FromRequestParts`/`FromRequest`.
- Missing principal is 401, never an anonymous fallback.
- Authorization (may this user do this to that object?) happens in the service, scoped by
  owner/tenant in the query (`database.md`, `security.md`).
- Token/cookie/CSRF/OIDC specifics: `security.md`.

## Observability

- `TraceLayer` creates a span per request; add the request id and matched path as span
  fields, never headers wholesale or bodies.
- The binary installs `tracing_subscriber` with `EnvFilter` (`RUST_LOG`), JSON output in
  production; OpenTelemetry (`tracing-opentelemetry`) when the project exports traces.
- `#[instrument(skip_all, fields(order_id = %id))]` on service methods worth a span.

## OpenAPI (optional)

When the project needs a spec: `utoipa` (derive-based, `utoipa-axum`) or `aide` — one
per project. Serve the docs UI only in non-production environments or behind auth.

## actix-web 4 — the same patterns

| Concern | axum 0.8 | actix-web 4 |
|---|---|---|
| Feature router | `Router::new().route("/orders/{id}", get(h))` | `web::scope("/orders").route("/{id}", web::get().to(h))`, registered via `App::configure(orders::http::configure)` |
| Path syntax | `{id}` | `{id}` (same) |
| Shared state | `State<Arc<Service>>` | `web::Data<Service>` (wraps an `Arc`) via `.app_data(web::Data::new(…))`; `web::ThinData<T>` for cheap-clone handles like pools |
| JSON body | `Json<T>`, limit via `DefaultBodyLimit` | `web::Json<T>`, limit via `.app_data(web::JsonConfig::default().limit(n).error_handler(…))` |
| Error → response | `impl IntoResponse for ApiError` | `impl ResponseError for ApiError` (`status_code`, `error_response`) |
| Custom extractor | `impl FromRequestParts<S>` with `async fn` | `impl FromRequest` (`type Future = Ready<Result<Self, Self::Error>>` for sync reads from extensions) |
| Middleware fn | `middleware::from_fn_with_state` | `actix_web::middleware::from_fn` + `.wrap(…)` |
| Layer order | last `.layer()` runs first | last `.wrap()` runs first |
| Tower ecosystem | tower-http layers | not available — `actix-cors`, `middleware::Compress`, `DefaultHeaders`, `tracing-actix-web` |
| Timeouts | `TimeoutLayer` | `HttpServer::client_request_timeout`, `keep_alive`; per-call `tokio::time::timeout` |
| Blocking work | `spawn_blocking` | `web::block` (or `spawn_blocking`) |
| Graceful shutdown | `with_graceful_shutdown(signal)` | built in: handles `SIGTERM`/`SIGINT`; set `.shutdown_timeout(secs)` |
| Entry point | `#[tokio::main]` | `#[actix_web::main]` |
| Handler tests | `tower::ServiceExt::oneshot` | `actix_web::test::init_service` + `call_service` |

actix-web runs one single-threaded runtime per worker: handler futures don't need to be
`Send`, but everything in `web::Data` is shared across workers and must be `Send + Sync`.
Domain, services, ports and adapters are identical for both frameworks — only `http.rs`
and `main.rs` differ.
