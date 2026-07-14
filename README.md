# Screenshot Scout Python SDK

The official Python SDK for the [Screenshot Scout](https://screenshotscout.com) screenshot API.
It provides typed blocking and async-I/O clients, exact GET and POST request serialization,
optional request signing, and access to both decoded results and the original buffered HTTP response.

## Requirements

Python 3.11 or newer.

## Installation

```shell
python -m pip install screenshotscout
```

## Quick start

Pass credentials to the client explicitly. The SDK does not read environment variables on its own.

```python
import os
from pathlib import Path

from screenshotscout import BinaryCaptureResponse, CaptureFormat, CaptureOptions, ScreenshotScoutClient

with ScreenshotScoutClient(os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]) as client:
    response = client.capture(
        "https://example.com",
        CaptureOptions(format=CaptureFormat.PNG, full_page=True),
    )

if not isinstance(response, BinaryCaptureResponse):
    raise RuntimeError("Expected a binary capture response")

Path("screenshot.png").write_bytes(response.bytes)
```

`capture()` uses POST by default. It buffers the response body before returning, so the result remains
usable after the client is closed.

## JSON responses

Request a JSON result when you want Screenshot Scout to return capture metadata instead of the binary
file directly:

```python
import os

from screenshotscout import (
    CaptureOptions,
    CaptureResponseType,
    CaptureStorageMode,
    JsonCaptureResponse,
    ScreenshotScoutClient,
)

options = CaptureOptions(
    response_type=CaptureResponseType.JSON,
    storage_mode=CaptureStorageMode.MANAGED,
)

with ScreenshotScoutClient(os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]) as client:
    response = client.capture("https://example.com", options)

if not isinstance(response, JsonCaptureResponse):
    raise RuntimeError("Expected a JSON capture response")

print(response.result.screenshot_url)
print(response.result.screenshot_url_expires_at)
print(response.result.cache_status)
```

Unrecognized JSON result properties are retained in `response.result.additional_fields`.

## Async Python client (inline response)

`AsyncScreenshotScoutClient` uses non-blocking Python and HTTPX I/O. `await capture()` still waits
for the final inline Screenshot Scout response; it does not submit a background screenshot job or
use webhooks. The client otherwise has the same capture and URL-building behavior as the blocking
client, and task cancellation is propagated unchanged.

```python
import asyncio
import os

from screenshotscout import AsyncScreenshotScoutClient, BinaryCaptureResponse, CaptureOptions


async def main() -> None:
    async with AsyncScreenshotScoutClient(os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]) as client:
        response = await client.capture(
            "https://example.com",
            CaptureOptions(full_page=True),
        )

    if isinstance(response, BinaryCaptureResponse):
        print(len(response.bytes))


asyncio.run(main())
```

## Client configuration

```python
import httpx

from screenshotscout import ScreenshotScoutClient

transport = httpx.Client()
client = ScreenshotScoutClient(
    "access_key",
    secret_key="secret_key",
    base_url="https://api.screenshotscout.com",
    request_timeout=httpx.Timeout(30.0, connect=10.0),
    http_client=transport,
)
```

- `access_key` is required and is sent as a Bearer credential for executed requests.
- `secret_key` is optional. When supplied, capture requests and generated capture URLs include an
  HMAC-SHA256 signature.
- `base_url` defaults to `https://api.screenshotscout.com`; `/v1/capture` is appended to it.
- By default, SDK-created clients have no HTTP timeout. An injected HTTPX client keeps its configured
  timeout. Set `request_timeout` to a positive number or `httpx.Timeout` to override it, or pass
  `None` to disable it explicitly.
- `http_client` accepts an `httpx.Client` for the blocking SDK or an `httpx.AsyncClient` for the
  async-I/O SDK. An injected client is never closed by the SDK; a client created internally is
  closed by `close()`, `aclose()`, or the corresponding context manager.

`CaptureOptions.timeout` and `CaptureOptions.navigation_timeout` are Screenshot Scout service
options. They are separate from the client-side `request_timeout` setting.

## GET requests and capture URLs

Use the closed `CaptureHTTPMethod` enum to execute a GET request:

```python
from screenshotscout import CaptureHTTPMethod

response = client.capture(
    "https://example.com",
    method=CaptureHTTPMethod.GET,
)
```

Executed GET and POST requests authenticate with the `Authorization` header. To create a capture URL
that can be used without that header, call `build_capture_url()`:

```python
capture_url = client.build_capture_url("https://example.com")
```

The generated URL contains the access key and may contain a signature. Treat it as sensitive: avoid
logging it, committing it, or exposing it to unintended recipients. Building a URL does not make a
network request.

## Capture options

Construct options with keyword arguments. `None` values and empty repeated values are omitted;
booleans, zero, and non-empty strings are preserved. Repeated options accept sequences and retain
their order. The SDK performs only structural serialization checks and leaves Screenshot Scout's
service semantics, defaults, and future string values to the API.

| Area | `CaptureOptions` fields |
|---|---|
| Output | `format`, `response_type` |
| Network and location | `country`, `proxy`, `geolocation_latitude`, `geolocation_longitude`, `geolocation_accuracy` |
| Cookies and headers | `cookies`, `headers` |
| Navigation and timing | `timeout`, `wait_until`, `navigation_timeout`, `delay` |
| Device emulation | `device`, `device_viewport_width`, `device_viewport_height`, `device_scale_factor`, `device_is_mobile`, `device_has_touch`, `device_user_agent` |
| Page preferences | `timezone`, `media_type`, `color_scheme`, `reduced_motion` |
| Full page | `full_page`, `full_page_pre_scroll`, `full_page_pre_scroll_step`, `full_page_pre_scroll_step_delay`, `full_page_max_height` |
| Blocking | `block_cookie_banners`, `block_ads`, `block_chat_widgets` |
| Interactions and injection | `hide_selectors`, `click_selectors`, `click_all_selectors`, `inject_css`, `inject_js`, `bypass_csp` |
| Selection and clipping | `selector`, `clip_x`, `clip_y`, `clip_width`, `clip_height` |
| Image output | `image_width`, `image_height`, `image_mode`, `image_anchor`, `image_allow_upscale`, `image_background`, `image_quality` |
| PDF output | `pdf_paper_format`, `pdf_landscape`, `pdf_print_background`, `pdf_margin`, `pdf_margin_top`, `pdf_margin_right`, `pdf_margin_bottom`, `pdf_margin_left`, `pdf_scale` |
| Caching | `cache`, `cache_ttl`, `cache_key` |
| Storage | `storage_mode`, `storage_endpoint`, `storage_bucket`, `storage_region`, `storage_object_key` |

The SDK provides discoverable constants for documented service values:

- `CaptureFormat`
- `CaptureResponseType`
- `CaptureWaitUntil`
- `CaptureMediaType`
- `CaptureColorScheme`
- `CaptureImageMode`
- `CaptureImageAnchor`
- `CapturePdfPaperFormat`
- `CaptureStorageMode`

These constants are strings, so raw strings remain supported for forward compatibility.

## Responses and raw HTTP data

Successful calls return one of two frozen response models:

- `BinaryCaptureResponse` exposes `bytes` and the documented screenshot URL, expiry, and cache-status
  response headers when present.
- `JsonCaptureResponse` exposes a typed `CaptureResult` and preserves additional result fields.

Both variants expose `raw_response`, which contains the status, reason phrase, multi-value headers,
content type, and exact buffered body. The `kind` discriminator is `"binary"` or `"json"`.

The SDK verifies that the successful response media type matches the requested response representation.

## Errors

All SDK-defined errors derive from `ScreenshotScoutError`:

- `ScreenshotScoutConfigurationError` — unusable credentials, base URL, timeout, client type, or a
  closed SDK client.
- `ScreenshotScoutSerializationError` — a request value cannot be represented safely on the wire.
- `ScreenshotScoutTransportError` — HTTPX failed before a complete response was received; the original
  exception is available as `cause`.
- `ScreenshotScoutAPIError` — the API returned a non-2xx response; parsed error fields and the exact
  `raw_response` are retained.
- `ScreenshotScoutResponseDecodingError` — a successful response has an incompatible media type or
  cannot be decoded as requested; `raw_response` is retained.

The SDK sends one request per `capture()` call. It does not retry, follow redirects, switch methods, or
normalize service option values.

## Examples

Runnable programs are available in [`examples`](examples):

- [`binary_capture.py`](examples/binary_capture.py)
- [`json_capture.py`](examples/json_capture.py)
- [`async_client.py`](examples/async_client.py)
- [`capture_url.py`](examples/capture_url.py)

## Development

Create a virtual environment and install the package with its development tools:

```shell
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the local checks:

```shell
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m pytest
python -m build
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
