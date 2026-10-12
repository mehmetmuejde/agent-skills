# Observability, logging and error handling

Code must be observable from its own output: structured logs at trust boundaries,
audit events for security-relevant actions, traces and metrics through OpenTelemetry.

## OpenTelemetry

Prefer FastAPI's native OpenTelemetry support:

- Install `fastapi[standard]` (includes the SDK and HTTP/protobuf exporters).
- Enable automatic exporter setup: `FASTAPI_OTEL_AUTO_CONFIGURE=true`.
- `OTEL_SERVICE_NAME` identifies the app; `OTEL_EXPORTER_OTLP_ENDPOINT` is the
  collector's HTTP/protobuf base URL; `OTEL_EXPORTER_OTLP_HEADERS` for auth.
- Custom configuration (signals, own providers): `FastAPI(telemetry={...})`.
- Providers configured by another telemetry library are picked up without auto setup.

## Structured logging

- Log as structured events (JSON in production), not free-text `print`.
- Every log line carries a request/correlation id; with OpenTelemetry the trace id.
- Times in UTC.
- **Never log**: passwords, tokens, session ids, API keys, full request/response bodies,
  full card numbers, health data. Log ids instead and redact known secret fields.

## Audit events

Security-relevant actions produce an audit event with
`who` (user id) · `what` (event name) · `target` (object id) · `outcome`
(granted/denied/failed) · `when` (UTC) · `where` (request id, client IP from the trusted
proxy header) — ASVS 16.2/16.3:

- logins, failed logins, logouts, password/MFA changes, session revocation,
- **denied** authorization decisions (BOLA/BFLA attempts are visible this way),
- admin actions, permission changes, data exports, deletions.

```python
log.info(
    "order.read.denied",
    user_id=str(user.id),
    order_id=str(order_id),
    reason="not_found_or_not_owned",
)
```

## Error handling

- Consumers get generic messages; details go to the log (ASVS 16.5.1).
- Raise `HTTPException` with deliberate status codes for expected cases; catch
  **specific** exceptions, never bare `except:` or `except Exception: pass`.
- Fail closed: if validation, authorization or an external check errors, the operation
  is rejected — never processed anyway (ASVS 16.5.3).
- Last-resort handler for everything unhandled (ASVS 16.5.4):

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

- External dependencies fail gracefully: timeouts, limited retries with backoff,
  degraded responses for non-critical features (ASVS 16.5.2).

## Health checks

Separate liveness (process is up) from readiness (DB and required services reachable).
Health and metrics endpoints are not public unless intended (ASVS 13.4.5).
