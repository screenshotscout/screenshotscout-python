"""Request a JSON Screenshot Scout capture result."""

import os

from screenshotscout import (
    CaptureOptions,
    CaptureResponseType,
    JsonCaptureResponse,
    ScreenshotScoutClient,
)


def main() -> None:
    options = CaptureOptions(response_type=CaptureResponseType.JSON)

    with ScreenshotScoutClient(os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]) as client:
        response = client.capture("https://example.com", options)

    if not isinstance(response, JsonCaptureResponse):
        raise RuntimeError("Expected a JSON capture response.")

    print(f"Screenshot URL: {response.result.screenshot_url}")


if __name__ == "__main__":
    main()
