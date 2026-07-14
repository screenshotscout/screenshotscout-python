"""Request a JSON Screenshot Scout capture result."""

import os

from screenshotscout import (
    CaptureOptions,
    CaptureResponseType,
    CaptureStorageMode,
    JsonCaptureResponse,
    ScreenshotScoutClient,
)


def main() -> None:
    options = CaptureOptions(
        response_type=CaptureResponseType.JSON,
        storage_mode=CaptureStorageMode.MANAGED,
    )

    with ScreenshotScoutClient(os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]) as client:
        response = client.capture("https://example.com", options)

    if not isinstance(response, JsonCaptureResponse):
        raise RuntimeError("Expected a JSON capture response.")

    print(f"Screenshot URL: {response.result.screenshot_url}")
    print(f"Expires at: {response.result.screenshot_url_expires_at}")
    print(f"Cache status: {response.result.cache_status}")


if __name__ == "__main__":
    main()
