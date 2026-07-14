"""Use async Python I/O while waiting for the inline capture response."""

import asyncio
import os

from screenshotscout import AsyncScreenshotScoutClient, BinaryCaptureResponse, CaptureOptions


async def main() -> None:
    options = CaptureOptions(full_page=True)

    async with AsyncScreenshotScoutClient(os.environ["SCREENSHOTSCOUT_ACCESS_KEY"]) as client:
        response = await client.capture("https://example.com", options)

    if not isinstance(response, BinaryCaptureResponse):
        raise RuntimeError("Expected a binary capture response.")

    print(f"Received {len(response.bytes)} bytes")


if __name__ == "__main__":
    asyncio.run(main())
