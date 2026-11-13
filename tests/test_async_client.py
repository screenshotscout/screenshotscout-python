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

# The same signing vector as in test_client.py, signed with ak_test and sk_test.
_EXPECTED_SIGNATURE = "6419f2ac8c0440f1e341b547630606c9dc74dacfbb2df8e122fc9ae26831d893"


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

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=20)
    async with http_client:
        async with AsyncScreenshotScoutClient(
            "key",
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
async def test_async_secret_key_sends_get_by_default_and_refuses_an_explicit_post() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"image", headers={"content-type": "image/png"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AsyncScreenshotScoutClient(
            "ak_test",
            secret_key="sk_test",
            http_client=http_client,
        )
        await client.capture("https://example.com")
        with pytest.raises(ScreenshotScoutConfigurationError, match="can't be signed"):
            await client.capture("https://example.com", method=CaptureHTTPMethod.POST)
        await client.aclose()

    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url.params.get("signature") is not None


@pytest.mark.asyncio
async def test_async_client_without_keys_reads_both_key_variables_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCREENSHOTSCOUT_ACCESS_KEY", "ak_test")
    monkeypatch.setenv("SCREENSHOTSCOUT_SECRET_KEY", "sk_test")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"{}", headers={"content-type": "application/json"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncScreenshotScoutClient(http_client=http_client) as client:
            monkeypatch.setenv("SCREENSHOTSCOUT_ACCESS_KEY", "changed")
            monkeypatch.setenv("SCREENSHOTSCOUT_SECRET_KEY", "changed")
            await client.capture(
                "https://example.com/a b?x=1&y=2",
                CaptureOptions(
                    response_type="json",
                    full_page=False,
                    delay=0,
                    headers=["X-Test:one", "X-Test:two"],
                ),
            )
            with pytest.raises(ScreenshotScoutConfigurationError) as explicit_post:
                await client.capture("https://example.com", method=CaptureHTTPMethod.POST)

    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].headers["authorization"] == "Bearer ak_test"
    assert requests[0].url.params["signature"] == _EXPECTED_SIGNATURE
    assert str(explicit_post.value) == (
        "POST requests can't be signed. This client has a secret key from "
        "SCREENSHOTSCOUT_SECRET_KEY: send this capture with method GET, or use a client without "
        "a secret key and an API key that doesn't require signed requests."
    )


def test_async_client_missing_access_key_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ScreenshotScoutConfigurationError) as missing:
        AsyncScreenshotScoutClient()
    monkeypatch.setenv("SCREENSHOTSCOUT_ACCESS_KEY", "ak_env")
    with pytest.raises(ScreenshotScoutConfigurationError) as secret_only:
        AsyncScreenshotScoutClient(secret_key="sk_code")

    assert str(missing.value) == (
        "A non-blank Screenshot Scout access key is required. Pass one, or set "
        "SCREENSHOTSCOUT_ACCESS_KEY."
    )
    assert str(secret_only.value) == "A non-blank Screenshot Scout access key is required."


def test_async_client_base_url_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ScreenshotScoutConfigurationError) as not_a_string:
        AsyncScreenshotScoutClient("key", base_url=cast(Any, 0))
    monkeypatch.setenv("SCREENSHOTSCOUT_BASE_URL", " ")
    with pytest.raises(ScreenshotScoutConfigurationError) as blank:
        AsyncScreenshotScoutClient("key")

    assert str(not_a_string.value) == (
        "The Screenshot Scout base URL must be a string when provided."
    )
    assert str(blank.value) == "SCREENSHOTSCOUT_BASE_URL is set but blank."


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


@pytest.mark.asyncio
async def test_async_base_url_sends_post_get_and_built_urls_to_that_server() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"image", headers={"content-type": "image/png"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncScreenshotScoutClient(
            "ak_test",
            base_url="http://localhost:8787/",
            http_client=http_client,
        ) as client:
            await client.capture("https://example.com")
            await client.capture("https://example.com", method=CaptureHTTPMethod.GET)
            built_url = client.build_capture_url("https://example.com")

    assert [request.method for request in requests] == ["POST", "GET"]
    assert [str(request.url) for request in requests] == [
        "http://localhost:8787/v1/capture",
        "http://localhost:8787/v1/capture?url=https%3A%2F%2Fexample.com",
    ]
    assert built_url == (
        "http://localhost:8787/v1/capture?access_key=ak_test&url=https%3A%2F%2Fexample.com"
    )


@pytest.mark.asyncio
async def test_async_base_url_keeps_its_path_and_leaves_signing_unchanged() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"{}", headers={"content-type": "application/json"})

    options = CaptureOptions(
        response_type="json",
        full_page=False,
        delay=0,
        headers=["X-Test:one", "X-Test:two"],
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncScreenshotScoutClient(
            "ak_test",
            secret_key="sk_test",
            base_url="https://proxy.example.com/screenshotscout//",
            http_client=http_client,
        ) as client:
            await client.capture("https://example.com/a b?x=1&y=2", options)
            built_url = client.build_capture_url("https://example.com/a b?x=1&y=2", options)

    assert requests[0].method == "GET"
    for url in (requests[0].url, httpx.URL(built_url)):
        assert url.host == "proxy.example.com"
        assert url.path == "/screenshotscout/v1/capture"
        assert url.params["signature"] == _EXPECTED_SIGNATURE


@pytest.mark.asyncio
async def test_async_client_reads_the_base_url_variable_once_even_with_keys_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCREENSHOTSCOUT_BASE_URL", "http://localhost:8787")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"image", headers={"content-type": "image/png"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        async with AsyncScreenshotScoutClient("ak_code", http_client=http_client) as client:
            monkeypatch.setenv("SCREENSHOTSCOUT_BASE_URL", "http://changed.example")
            await client.capture("https://example.com")
            built_url = client.build_capture_url("https://example.com")

    assert str(requests[0].url) == "http://localhost:8787/v1/capture"
    assert built_url == (
        "http://localhost:8787/v1/capture?access_key=ak_code&url=https%3A%2F%2Fexample.com"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("variable", "base_url", "suffix"),
    [
        (None, None, ""),
        ("http://localhost:8787", None, " The base URL comes from SCREENSHOTSCOUT_BASE_URL."),
        ("http://localhost:8787", "http://localhost:8787", ""),
    ],
    ids=["api", "variable", "passed"],
)
async def test_async_transport_failure_names_the_base_url_variable_only_when_it_was_used(
    monkeypatch: pytest.MonkeyPatch,
    variable: str | None,
    base_url: str | None,
    suffix: str,
) -> None:
    native_cause = RuntimeError("network unavailable")

    async def handler(_request: httpx.Request) -> httpx.Response:
        raise native_cause

    if variable is not None:
        monkeypatch.setenv("SCREENSHOTSCOUT_BASE_URL", variable)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = AsyncScreenshotScoutClient("key", base_url=base_url, http_client=http_client)
        with pytest.raises(ScreenshotScoutTransportError) as captured:
            await client.capture("https://example.com")
        await client.aclose()

    assert str(captured.value) == (
        f"Screenshot Scout request failed before an HTTP response body was received.{suffix}"
    )
    assert captured.value.cause is native_cause
    assert captured.value.__cause__ is native_cause


@pytest.mark.asyncio
async def test_asyncio_cancellation_is_not_wrapped_with_the_base_url_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCREENSHOTSCOUT_BASE_URL", "http://localhost:8787")
    started = asyncio.Event()
    never = asyncio.Event()

    async def handler(_request: httpx.Request) -> httpx.Response:
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


@pytest.mark.asyncio
async def test_async_malformed_base_url_is_a_transport_error_and_built_as_given() -> None:
    # The SDK's own HTTPX client rejects the URL before connecting to anything.
    async with AsyncScreenshotScoutClient("key", base_url="not a url") as client:
        with pytest.raises(ScreenshotScoutTransportError) as captured:
            await client.capture("https://example.com")
        built_url = client.build_capture_url("https://example.com")

    assert isinstance(captured.value.cause, httpx.UnsupportedProtocol)
    assert captured.value.__cause__ is captured.value.cause
    assert built_url == "not a url/v1/capture?access_key=key&url=https%3A%2F%2Fexample.com"


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


@pytest.mark.asyncio
async def test_injected_async_client_timeout_is_preserved() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=b"image", headers={"content-type": "image/png"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        timeout=7.0,
    ) as http_client:
        async with AsyncScreenshotScoutClient("key", http_client=http_client) as client:
            await client.capture("https://example.com")

    timeout = cast(dict[str, float | None], requests[0].extensions["timeout"])
    assert timeout == {
        "connect": 7.0,
        "read": 7.0,
        "write": 7.0,
        "pool": 7.0,
    }
