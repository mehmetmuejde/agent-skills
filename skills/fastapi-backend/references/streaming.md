# Streaming

Declare the return type and `yield` the items — FastAPI serializes each item with
Pydantic. Don't build and return a `StreamingResponse` object by hand.

## JSON Lines

```python
from collections.abc import AsyncIterable


@router.get("/items/stream")
async def stream_items() -> AsyncIterable[Item]:
    for item in items:
        yield item
```

## Server-Sent Events (SSE)

Use `response_class=EventSourceResponse` and `yield`. Plain objects become JSON `data:`
fields:

```python
from collections.abc import AsyncIterable

from fastapi.sse import EventSourceResponse, ServerSentEvent


@router.get("/items/stream", response_class=EventSourceResponse)
async def stream_items() -> AsyncIterable[Item]:
    yield Item(name="Plumbus", price=32.99)
```

For full control over `event`, `id`, `retry` and `comment`, yield `ServerSentEvent`:

```python
@router.get("/events", response_class=EventSourceResponse)
async def stream_events() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(data={"status": "started"}, event="status", id="1")
    yield ServerSentEvent(data={"progress": 50}, event="progress", id="2")
```

`raw_data=` sends a pre-formatted string without JSON encoding.

## Bytes

Declare a `StreamingResponse` subclass as `response_class` and `yield` the chunks:

```python
class PNGStreamingResponse(StreamingResponse):
    media_type = "image/png"


@router.get("/image", response_class=PNGStreamingResponse)
def stream_image():
    with read_image() as image_file:
        yield from image_file
```

## Rules for long-lived streams

- Streams are authenticated and authorized like any endpoint — the dependency runs once
  at the start, so re-check permissions for very long streams if revocation matters.
- Limit concurrent streams per user and set a maximum duration (API4).
- Blocking work inside an `async` generator stalls the loop — use a sync generator
  (`def` + `yield`) or `asyncify`.
- Clean up resources in `try/finally` inside the generator — the client may disconnect
  at any time.
