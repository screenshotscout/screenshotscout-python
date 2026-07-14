# Screenshot Scout Python SDK

The official Python SDK for the [Screenshot Scout](https://screenshotscout.com/) screenshot API.
Easily capture website screenshots from your Python applications.

## Requirements

Python 3.11 or newer.

## Installation

```shell
python -m pip install screenshotscout
```

## Get your API credentials

Before using the SDK, [sign up for Screenshot Scout](https://screenshotscout.com/) or sign in to
your existing account. Screenshot Scout automatically creates a default API key when you sign up.

Open the [API Keys page](https://screenshotscout.com/app/api-keys), copy the access key and secret
key, and store them securely. The access key is required when creating `ScreenshotScoutClient` or
`AsyncScreenshotScoutClient`. The secret key is optional and enables
[signed requests](#signed-requests).

## Capture a screenshot

Read your access key from an environment variable and pass it to the client:

```python
import os
from pathlib import Path

from screenshotscout import (
    BinaryCaptureResponse,
    CaptureFormat,
    CaptureOptions,
    ScreenshotScoutClient,
)

access_key = os.environ.get("SCREENSHOTSCOUT_ACCESS_KEY")
if not access_key:
    raise RuntimeError("Set SCREENSHOTSCOUT_ACCESS_KEY first.")

with ScreenshotScoutClient(access_key) as client:
    response = client.capture(
        "https://example.com",
        CaptureOptions(format=CaptureFormat.WEBP, full_page=True),
    )

if not isinstance(response, BinaryCaptureResponse):
    raise RuntimeError("Expected a binary capture response")

Path("screenshot.webp").write_bytes(response.bytes)
```

POST is used by default. The screenshot is available as `response.bytes`.

## Request a JSON result

Set `response_type` to `CaptureResponseType.JSON` to receive screenshot metadata instead of the
binary file:

```python
import os

from screenshotscout import (
    CaptureOptions,
    CaptureResponseType,
    JsonCaptureResponse,
    ScreenshotScoutClient,
)

options = CaptureOptions(response_type=CaptureResponseType.JSON)

with ScreenshotScoutClient(os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]) as client:
    response = client.capture("https://example.com", options)

if not isinstance(response, JsonCaptureResponse):
    raise RuntimeError("Expected a JSON capture response")

print(response.result.screenshot_url)
```

## Async client

Use `AsyncScreenshotScoutClient` in applications that use `asyncio`. `await capture()` waits for
and returns the completed capture; it does not create a background job.

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

## Use GET

POST is the default. Pass `CaptureHTTPMethod.GET` when you need a GET request:

```python
from screenshotscout import CaptureHTTPMethod

response = client.capture(
    "https://example.com",
    method=CaptureHTTPMethod.GET,
)
```

## Build a capture URL

Use `build_capture_url()` when a browser, an HTML `<img>` element, or another application needs to
load the screenshot directly. Building the URL does not make a request.

```python
from screenshotscout import CaptureOptions

capture_url = client.build_capture_url(
    "https://example.com",
    CaptureOptions(full_page=True, block_ads=True),
)
```

The generated URL contains your access key. If the client has a secret key, the URL is signed
automatically; otherwise, it is unsigned. Treat generated URLs as sensitive. Before exposing one
to a browser or user, add your secret key to the client and enable **Require signed requests** on
the [API Keys page](https://screenshotscout.com/app/api-keys).

## Signed requests

Pass your secret key to sign GET and POST requests and generated capture URLs automatically. The
secret key stays in your application and is never transmitted.

```python
import os

from screenshotscout import ScreenshotScoutClient

with ScreenshotScoutClient(
    os.environ["SCREENSHOTSCOUT_ACCESS_KEY"],
    secret_key=os.environ["SCREENSHOTSCOUT_SECRET_KEY"],
) as client:
    response = client.capture("https://example.com")
```

See the [signed requests guide](https://screenshotscout.com/docs/signed-requests) for details.

## Capture options

The target URL is the first argument to `capture()`. Use `CaptureOptions` keyword arguments to
customize the screenshot:

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

Use the provided constants for autocomplete, or pass a string:

```python
from screenshotscout import CaptureFormat, CaptureOptions, CaptureWaitUntil

options = CaptureOptions(
    format=CaptureFormat.WEBP,
    wait_until=CaptureWaitUntil.LOAD,
)
response = client.capture("https://example.com", options)
```

See the [screenshot option reference](https://screenshotscout.com/docs/screenshot-options) for
available values and examples.

## Timeouts

```python
import os

from screenshotscout import CaptureOptions, ScreenshotScoutClient

with ScreenshotScoutClient(
    os.environ["SCREENSHOTSCOUT_ACCESS_KEY"],
    request_timeout=300.0,
) as client:
    response = client.capture(
        "https://example.com",
        CaptureOptions(timeout=180),
    )
```

`CaptureOptions.timeout` controls how long Screenshot Scout may spend capturing the page.
`request_timeout` controls how long your application waits for the API response.

## Responses

- `BinaryCaptureResponse` provides the screenshot as `bytes`, along with URL, expiry, and cache
  information when available.
- `JsonCaptureResponse` provides screenshot metadata in `result`.

Both response types include `raw_response` for access to the HTTP status, headers, content type,
and body.

## Error handling

```python
import os

from screenshotscout import (
    ScreenshotScoutAPIError,
    ScreenshotScoutClient,
    ScreenshotScoutError,
    ScreenshotScoutTransportError,
)

try:
    with ScreenshotScoutClient(os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]) as client:
        response = client.capture("https://example.com")
except ScreenshotScoutAPIError as error:
    print(error.status, error.error_code, error.error_message)
except ScreenshotScoutTransportError as error:
    print(error.cause)
except ScreenshotScoutError as error:
    print(error)
```

The SDK does not automatically retry failed requests.

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
