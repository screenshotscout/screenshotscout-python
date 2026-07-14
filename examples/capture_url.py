"""Build a sensitive Screenshot Scout capture URL without sending a request."""

import os

from screenshotscout import CaptureOptions, ScreenshotScoutClient


def main() -> None:
    access_key = os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]
    secret_key = os.environ.get("SCREENSHOTSCOUT_SECRET_KEY")
    options = CaptureOptions(full_page=True)

    with ScreenshotScoutClient(access_key, secret_key=secret_key) as client:
        capture_url = client.build_capture_url("https://example.com", options)

    print("Sensitive capture URL (do not log or commit it):")
    print(capture_url)


if __name__ == "__main__":
    main()
