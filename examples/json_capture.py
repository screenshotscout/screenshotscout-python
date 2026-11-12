"""Request a JSON Screenshot Scout capture result."""

from screenshotscout import (
    CaptureOptions,
    CaptureResponseType,
    JsonCaptureResponse,
    ScreenshotScoutClient,
)


def main() -> None:
    options = CaptureOptions(response_type=CaptureResponseType.JSON)

    with ScreenshotScoutClient() as client:  # Reads SCREENSHOTSCOUT_ACCESS_KEY
        response = client.capture("https://example.com", options)

    if not isinstance(response, JsonCaptureResponse):
        raise RuntimeError("Expected a JSON capture response.")

    print(f"Screenshot URL: {response.result.screenshot_url}")


if __name__ == "__main__":
    main()
