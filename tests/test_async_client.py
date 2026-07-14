from __future__ import annotations

import asyncio
import json
from typing import Any, cast

import httpx
import pytest

from screenshotscout import (
    AsyncScreenshotScoutClient,
    CaptureHTTPMethod,
    CaptureOptions,
    JsonCaptureResponse,
    ScreenshotScoutConfigurationError,
    ScreenshotScoutTransportError,
)


@pytest.mark.asyncio
async def test_async_client_uses_same_post_and_response_behavior() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "screenshot_url": "https://cdn.example/a.png",
                "request_id": "request-1",
            },
            headers={"content-type": "application/json"},
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with http_client:
        async with AsyncScreenshotScoutClient(
            "key",
            request_timeout=20,
            http_client=http_client,
        ) as client:
            response = await client.capture(
                "https://example.com",
                CaptureOptions(response_type="json", full_page=False),
            )
        assert not http_client.is_closed

    assert isinstance(response, JsonCaptureResponse)
    assert response.result.screenshot_url == "https://cdn.example/a.png"
    assert response.result.additional_fields == {"request_id": "request-1"}
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].headers["authorization"] == "Bearer key"
    body: Any = json.loads(requests[0].content)
    assert body == {
        "url": "https://example.com",
        "response_type": "json",
        "full_page": False,
    }
    timeout = cast(dict[str, float | None], requests[0].extensions["timeout"])
    assert timeout["read"] == 20
    with pytest.raises(ScreenshotScoutConfigurationError, match="closed"):
        await client.capture("https://example.com")


@pytest.mark.asyncio
async def test_async_get_and_url_builder_use_closed_method_and_signing() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            content=b"image",
            headers={"content-type": "image/png"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AsyncScreenshotScoutClient(
            "ak_test",
            secret_key="sk_test",
            http_client=http_client,
        )
        await client.capture(
            "https://example.com",
            CaptureOptions(full_page=False),
            method=CaptureHTTPMethod.GET,
        )
        capture_url = client.build_capture_url(
            "https://example.com",
            CaptureOptions(full_page=False),
        )
        await client.aclose()

    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url.params.get("signature") is not None
    assert "access_key=ak_test" in capture_url
    assert "signature=" in capture_url


@pytest.mark.asyncio
async def test_async_transport_failure_retains_cause() -> None:
    native_cause = RuntimeError("network unavailable")

    async def handler(_request: httpx.Request) -> httpx.Response:
        raise native_cause

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AsyncScreenshotScoutClient("key", http_client=http_client)
        with pytest.raises(ScreenshotScoutTransportError) as captured:
            await client.capture("https://example.com")
        await client.aclose()

    assert captured.value.cause is native_cause
    assert captured.value.__cause__ is native_cause


@pytest.mark.asyncio
async def test_asyncio_cancellation_is_not_wrapped() -> None:
    started = asyncio.Event()
    never = asyncio.Event()
    calls = 0

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        started.set()
        await never.wait()
        raise AssertionError("unreachable")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AsyncScreenshotScoutClient("key", http_client=http_client)
        task = asyncio.create_task(client.capture("https://example.com"))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await client.aclose()

    assert calls == 1


def test_async_client_rejects_sync_httpx_client() -> None:
    with httpx.Client() as sync_client:
        with pytest.raises(ScreenshotScoutConfigurationError, match="httpx.AsyncClient"):
            AsyncScreenshotScoutClient("key", http_client=cast(Any, sync_client))


@pytest.mark.asyncio
async def test_injected_async_http_client_truth_value_is_not_evaluated() -> None:
    class NonBooleanAsyncClient(httpx.AsyncClient):
        def __bool__(self) -> bool:
            raise AssertionError("An injected async HTTP client must not be used as a condition.")

    async with NonBooleanAsyncClient() as http_client:
        client = AsyncScreenshotScoutClient("key", http_client=http_client)
        await client.aclose()

        assert not http_client.is_closed
