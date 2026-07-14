"""Save a binary Screenshot Scout capture to screenshot.png."""

import os
from pathlib import Path

from screenshotscout import (
    BinaryCaptureResponse,
    CaptureFormat,
    CaptureOptions,
    ScreenshotScoutClient,
)


def main() -> None:
    access_key = os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]
    options = CaptureOptions(format=CaptureFormat.PNG, full_page=True)

    with ScreenshotScoutClient(access_key) as client:
        response = client.capture("https://example.com", options)

    if not isinstance(response, BinaryCaptureResponse):
        raise RuntimeError("Expected a binary capture response.")

    output = Path("screenshot.png")
    output.write_bytes(response.bytes)
    print(f"Saved {len(response.bytes)} bytes to {output}")


if __name__ == "__main__":
    main()
