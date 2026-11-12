"""Build a sensitive Screenshot Scout capture URL without sending a request."""

from screenshotscout import CaptureOptions, ScreenshotScoutClient


def main() -> None:
    options = CaptureOptions(full_page=True)

    # Reads SCREENSHOTSCOUT_ACCESS_KEY, and SCREENSHOTSCOUT_SECRET_KEY if it's set
    with ScreenshotScoutClient() as client:
        capture_url = client.build_capture_url("https://example.com", options)

    print("Sensitive capture URL (do not log or commit it):")
    print(capture_url)


if __name__ == "__main__":
    main()
