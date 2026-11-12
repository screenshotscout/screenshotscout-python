"""Save a binary Screenshot Scout capture to screenshot.webp."""

from pathlib import Path

from screenshotscout import (
    BinaryCaptureResponse,
    CaptureFormat,
    CaptureOptions,
    ScreenshotScoutClient,
)


def main() -> None:
    options = CaptureOptions(format=CaptureFormat.WEBP, full_page=True)

    with ScreenshotScoutClient() as client:  # Reads SCREENSHOTSCOUT_ACCESS_KEY
        response = client.capture("https://example.com", options)

    if not isinstance(response, BinaryCaptureResponse):
        raise RuntimeError("Expected a binary capture response.")

    output = Path("screenshot.webp")
    output.write_bytes(response.bytes)
    print(f"Saved {len(response.bytes)} bytes to {output}")


if __name__ == "__main__":
    main()
