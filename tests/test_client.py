from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest

from screenshotscout import (
    BinaryCaptureResponse,
    CaptureFormat,
    CaptureHTTPMethod,
    CaptureOptions,
    CaptureResponseType,
    JsonCaptureResponse,
    RequestTimeout,
    ScreenshotScoutAPIError,
    ScreenshotScoutClient,
    ScreenshotScoutConfigurationError,
    ScreenshotScoutResponseDecodingError,
    ScreenshotScoutSerializationError,
    ScreenshotScoutTransportError,
)

ResponseFactory = Callable[[httpx.Request], httpx.Response]


def _default_response(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        content=b"\x01",
        headers={"content-type": "image/png"},
    )


def _recording_http_client(
    response_factory: ResponseFactory = _default_response,
) -> tuple[httpx.Client, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response_factory(request)

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def _json_request_body(request: httpx.Request) -> dict[str, Any]:
    value: Any = json.loads(request.content)
    assert isinstance(value, dict)
    return value


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("",), "access key"),
        (("   ",), "access key"),
        (("key with spaces",), "Bearer credential"),
        (("key",), None),
    ],
)
def test_configuration_validates_access_key(
    arguments: tuple[str],
    message: str | None,
) -> None:
    if message is None:
        with ScreenshotScoutClient(*arguments):
            pass
        return

    with pytest.raises(ScreenshotScoutConfigurationError, match=message):
        ScreenshotScoutClient(*arguments)


def test_configuration_validates_optional_values() -> None:
    request_timeout: RequestTimeout = httpx.Timeout(1)
    with ScreenshotScoutClient("key", request_timeout=request_timeout):
        pass

    with pytest.raises(ScreenshotScoutConfigurationError, match="secret key"):
        ScreenshotScoutClient("key", secret_key="")
    with pytest.raises(ScreenshotScoutConfigurationError, match="base_url"):
        ScreenshotScoutClient("key", base_url="relative")
    with pytest.raises(ScreenshotScoutConfigurationError, match="query string"):
        ScreenshotScoutClient("key", base_url="https://api.example.test?x=1")
    with pytest.raises(ScreenshotScoutConfigurationError, match="request_timeout"):
        ScreenshotScoutClient("key", request_timeout=float("inf"))
    with pytest.raises(ScreenshotScoutConfigurationError, match="httpx.Client"):
        ScreenshotScoutClient("key", http_client=cast(Any, object()))


def test_injected_http_client_truth_value_is_not_evaluated() -> None:
    class NonBooleanClient(httpx.Client):
        def __bool__(self) -> bool:
            raise AssertionError("An injected HTTP client must not be used as a condition.")

    with NonBooleanClient() as http_client:
        client = ScreenshotScoutClient("key", http_client=http_client)
        client.close()

        assert not http_client.is_closed


def test_injected_http_client_timeout_inheritance_and_explicit_disable() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _default_response(request)

    with httpx.Client(transport=httpx.MockTransport(handler), timeout=7.0) as http_client:
        inherited_client = ScreenshotScoutClient("key", http_client=http_client)
        inherited_client.capture("https://example.com")
        inherited_client.close()

        timeout_free_client = ScreenshotScoutClient(
            "key",
            request_timeout=None,
            http_client=http_client,
        )
        timeout_free_client.capture("https://example.com")
        timeout_free_client.close()

    inherited_timeout = cast(dict[str, float | None], requests[0].extensions["timeout"])
    disabled_timeout = cast(dict[str, float | None], requests[1].extensions["timeout"])
    assert inherited_timeout == {
        "connect": 7.0,
        "read": 7.0,
        "write": 7.0,
        "pool": 7.0,
    }
    assert disabled_timeout == {
        "connect": None,
        "read": None,
        "write": None,
        "pool": None,
    }


def test_post_is_default_and_serializes_complete_option_surface() -> None:
    http_client, requests = _recording_http_client()
    options = CaptureOptions(
        format="future-format",
        response_type="future-response",
        country="",
        proxy="",
        geolocation_latitude=0,
        geolocation_longitude=0,
        geolocation_accuracy=0,
        cookies=["session=a", "session=a", ""],
        headers=["X-Test:one", "X-Test:one", ""],
        timeout=0,
        wait_until="future-wait-state",
        navigation_timeout=0,
        delay=0,
        device="",
        device_viewport_width=0,
        device_viewport_height=0,
        device_scale_factor=0,
        device_is_mobile=False,
        device_has_touch=False,
        device_user_agent="",
        timezone="",
        media_type="future-media",
        color_scheme="future-scheme",
        reduced_motion=False,
        full_page=False,
        full_page_pre_scroll=False,
        full_page_pre_scroll_step=0,
        full_page_pre_scroll_step_delay=0,
        full_page_max_height=0,
        block_cookie_banners=False,
        block_ads=False,
        block_chat_widgets=False,
        hide_selectors=[".same", ".same", ""],
        click_selectors=["#first", "#first", ""],
        click_all_selectors=[".all", ".all", ""],
        inject_css=["", "body { color: red; }"],
        inject_js=["", "document.title = 'x';"],
        bypass_csp=False,
        selector="",
        clip_x=0,
        clip_y=0,
        clip_width=0,
        clip_height=0,
        image_width=0,
        image_height=0,
        image_mode="future-image-mode",
        image_anchor="future-anchor",
        image_allow_upscale=False,
        image_background="",
        image_quality=0,
        pdf_paper_format="future-paper",
        pdf_landscape=False,
        pdf_print_background=False,
        pdf_margin="",
        pdf_margin_top="",
        pdf_margin_right="",
        pdf_margin_bottom="",
        pdf_margin_left="",
        pdf_scale=0,
        cache=False,
        cache_ttl=0,
        cache_key="",
        storage_mode="future-storage",
        storage_endpoint="",
        storage_bucket="",
        storage_region="",
        storage_object_key="",
    )

    try:
        client = ScreenshotScoutClient("access-key", http_client=http_client)
        response = client.capture("", options)
    finally:
        http_client.close()

    assert isinstance(response, BinaryCaptureResponse)
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.screenshotscout.com/v1/capture"
    assert request.method == "POST"
    assert request.headers["authorization"] == "Bearer access-key"
    assert request.headers["content-type"] == "application/json"
    assert _json_request_body(request) == {
        "url": "",
        "format": "future-format",
        "response_type": "future-response",
        "country": "",
        "proxy": "",
        "geolocation_latitude": 0,
        "geolocation_longitude": 0,
        "geolocation_accuracy": 0,
        "cookies": ["session=a", "session=a", ""],
        "headers": ["X-Test:one", "X-Test:one", ""],
        "timeout": 0,
        "wait_until": "future-wait-state",
        "navigation_timeout": 0,
        "delay": 0,
        "device": "",
        "device_viewport_width": 0,
        "device_viewport_height": 0,
        "device_scale_factor": 0,
        "device_is_mobile": False,
        "device_has_touch": False,
        "device_user_agent": "",
        "timezone": "",
        "media_type": "future-media",
        "color_scheme": "future-scheme",
        "reduced_motion": False,
        "full_page": False,
        "full_page_pre_scroll": False,
        "full_page_pre_scroll_step": 0,
        "full_page_pre_scroll_step_delay": 0,
        "full_page_max_height": 0,
        "block_cookie_banners": False,
        "block_ads": False,
        "block_chat_widgets": False,
        "hide_selectors": [".same", ".same", ""],
        "click_selectors": ["#first", "#first", ""],
        "click_all_selectors": [".all", ".all", ""],
        "inject_css": ["", "body { color: red; }"],
        "inject_js": ["", "document.title = 'x';"],
        "bypass_csp": False,
        "selector": "",
        "clip_x": 0,
        "clip_y": 0,
        "clip_width": 0,
        "clip_height": 0,
        "image_width": 0,
        "image_height": 0,
        "image_mode": "future-image-mode",
        "image_anchor": "future-anchor",
        "image_allow_upscale": False,
        "image_background": "",
        "image_quality": 0,
        "pdf_paper_format": "future-paper",
        "pdf_landscape": False,
        "pdf_print_background": False,
        "pdf_margin": "",
        "pdf_margin_top": "",
        "pdf_margin_right": "",
        "pdf_margin_bottom": "",
        "pdf_margin_left": "",
        "pdf_scale": 0,
        "cache": False,
        "cache_ttl": 0,
        "cache_key": "",
        "storage_mode": "future-storage",
        "storage_endpoint": "",
        "storage_bucket": "",
        "storage_region": "",
        "storage_object_key": "",
    }


def test_capture_options_subclass_fields_are_not_serialized() -> None:
    @dataclass(slots=True, kw_only=True)
    class ExtendedCaptureOptions(CaptureOptions):
        local_note: str | None = None

    http_client, requests = _recording_http_client()
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        client.capture(
            "https://example.com",
            ExtendedCaptureOptions(full_page=False, local_note="local only"),
        )
        client.close()
    finally:
        http_client.close()

    assert _json_request_body(requests[0]) == {
        "url": "https://example.com",
        "full_page": False,
    }


def test_none_and_empty_repeated_options_are_omitted_without_defaults() -> None:
    http_client, requests = _recording_http_client()
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        client.capture(
            "https://example.com",
            CaptureOptions(
                format=None,
                cookies=[],
                headers=(),
                hide_selectors=[],
                click_selectors=(),
                click_all_selectors=[],
                inject_css=(),
                inject_js=[],
            ),
        )
    finally:
        http_client.close()

    assert _json_request_body(requests[0]) == {"url": "https://example.com"}


def test_get_preserves_repeated_values_and_uses_bearer_authentication() -> None:
    http_client, requests = _recording_http_client()
    try:
        client = ScreenshotScoutClient("query-secret", http_client=http_client)
        client.capture(
            "https://example.com/a path~",
            CaptureOptions(
                cookies=["a=1", "a=1"],
                headers=["X-Test:one", "X-Test:one"],
                delay=0,
                full_page=False,
                cache_key="",
            ),
            method=CaptureHTTPMethod.GET,
        )
    finally:
        http_client.close()

    request = requests[0]
    assert request.method == "GET"
    assert request.content == b""
    assert request.headers["authorization"] == "Bearer query-secret"
    assert "content-type" not in request.headers
    assert request.url.params.get_list("cookies") == ["a=1", "a=1"]
    assert request.url.params.get_list("headers") == ["X-Test:one", "X-Test:one"]
    assert request.url.params.get("access_key") is None
    assert request.url.params.get("signature") is None
    assert request.url.query.decode("ascii") == (
        "url=https%3A%2F%2Fexample.com%2Fa+path%7E"
        "&cookies=a%3D1&cookies=a%3D1"
        "&headers=X-Test%3Aone&headers=X-Test%3Aone"
        "&delay=0&full_page=false&cache_key="
    )


def test_build_capture_url_is_pure_and_unsigned_without_secret_key() -> None:
    http_client, requests = _recording_http_client()
    try:
        client = ScreenshotScoutClient("query-key", http_client=http_client)
        capture_url = client.build_capture_url(
            "https://example.com/a path",
            CaptureOptions(
                cookies=["a=1", "a=1"],
                headers=["X-Test:one", "X-Test:one"],
                delay=0,
                full_page=False,
                cache_key="",
            ),
        )
    finally:
        http_client.close()

    parsed = urlsplit(capture_url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    assert requests == []
    assert parsed.scheme == "https"
    assert parsed.netloc == "api.screenshotscout.com"
    assert parsed.path == "/v1/capture"
    assert pairs[:2] == [
        ("access_key", "query-key"),
        ("url", "https://example.com/a path"),
    ]
    assert [value for name, value in pairs if name == "cookies"] == ["a=1", "a=1"]
    assert not any(name == "signature" for name, _ in pairs)


@pytest.mark.parametrize(
    ("target_url", "options", "method", "option"),
    [
        (123, CaptureOptions(), CaptureHTTPMethod.POST, "url"),
        ("https://example.com", cast(Any, {"format": "png"}), CaptureHTTPMethod.POST, None),
        (
            "https://example.com",
            CaptureOptions(format=cast(Any, {"value": "png"})),
            CaptureHTTPMethod.POST,
            "format",
        ),
        (
            "https://example.com",
            CaptureOptions(image_width=cast(Any, float("inf"))),
            CaptureHTTPMethod.POST,
            "image_width",
        ),
        (
            "https://example.com",
            CaptureOptions(headers=cast(Any, ["x:y", 1])),
            CaptureHTTPMethod.POST,
            "headers",
        ),
        (
            "https://example.com",
            CaptureOptions(image_width=cast(Any, 10**30)),
            CaptureHTTPMethod.POST,
            "image_width",
        ),
        ("https://example.com", CaptureOptions(), cast(Any, "GET"), "method"),
    ],
)
def test_unsafe_structures_fail_before_transport(
    target_url: object,
    options: CaptureOptions,
    method: CaptureHTTPMethod,
    option: str | None,
) -> None:
    http_client, requests = _recording_http_client()
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        with pytest.raises(ScreenshotScoutSerializationError) as captured:
            client.capture(cast(Any, target_url), options, method=method)
    finally:
        http_client.close()

    assert captured.value.option == option
    assert requests == []


def test_signing_matches_the_api_and_node_interoperability_vector() -> None:
    def json_response(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"{}",
            headers={"content-type": "application/json"},
        )

    http_client, requests = _recording_http_client(json_response)
    options = CaptureOptions(
        response_type="json",
        full_page=False,
        delay=0,
        headers=["X-Test:one", "X-Test:two"],
    )
    target_url = "https://example.com/a b?x=1&y=2"
    expected_signature = "0c4928ba691575903f27b911b8ea1a536604ca070d60d886e10c127c05e236fc"

    try:
        client = ScreenshotScoutClient(
            "ak_test",
            secret_key="sk_test",
            http_client=http_client,
        )
        client.capture(target_url, options, method=CaptureHTTPMethod.GET)
        client.capture(target_url, options, method=CaptureHTTPMethod.POST)
        built_url = client.build_capture_url(target_url, options)
    finally:
        http_client.close()

    assert requests[0].url.params["signature"] == expected_signature
    assert _json_request_body(requests[1])["signature"] == expected_signature
    assert dict(parse_qsl(urlsplit(built_url).query))["signature"] == expected_signature
    assert "sk_test" not in built_url
    assert requests[0].url.params.get("access_key") is None
    assert "access_key" not in _json_request_body(requests[1])


def test_default_binary_response_retains_bytes_metadata_and_raw_response() -> None:
    def response_factory(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            content=bytes([0, 1, 2, 255]),
            headers=[
                ("content-type", "image/png"),
                ("screenshot-scout-cache-status", "HIT"),
                (
                    "screenshot-scout-screenshot-url",
                    "https://cdn.example/screenshot.png",
                ),
                (
                    "screenshot-scout-screenshot-url-expires-at",
                    "2026-07-14T00:00:00Z",
                ),
                ("set-cookie", "a=1; Path=/"),
                ("set-cookie", "b=2; Path=/"),
            ],
        )

    http_client, _ = _recording_http_client(response_factory)
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        response = client.capture("https://example.com")
    finally:
        http_client.close()

    assert isinstance(response, BinaryCaptureResponse)
    assert response.kind == "binary"
    assert response.bytes == bytes([0, 1, 2, 255])
    assert response.screenshot_url == "https://cdn.example/screenshot.png"
    assert response.screenshot_url_expires_at == "2026-07-14T00:00:00Z"
    assert response.cache_status == "HIT"
    assert response.raw_response.status == 201
    assert response.raw_response.status_text == "Created"
    assert response.raw_response.content_type == "image/png"
    assert response.raw_response.body == bytes([0, 1, 2, 255])
    assert response.raw_response.headers["set-cookie"] == (
        "a=1; Path=/",
        "b=2; Path=/",
    )


def test_explicit_json_response_retains_documented_and_additional_fields() -> None:
    body = {
        "screenshot_url": "https://cdn.example/screenshot.png",
        "cache_status": "miss",
        "request_id": "request-123",
        "future": {"nested": True},
    }

    def response_factory(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=body,
            headers={"content-type": "application/vnd.screenshotscout+json; charset=utf-8"},
        )

    http_client, _ = _recording_http_client(response_factory)
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        response = client.capture(
            "https://example.com",
            CaptureOptions(response_type=CaptureResponseType.JSON),
        )
    finally:
        http_client.close()

    assert isinstance(response, JsonCaptureResponse)
    assert response.kind == "json"
    assert response.result.screenshot_url == "https://cdn.example/screenshot.png"
    assert response.result.screenshot_url_expires_at is None
    assert response.result.cache_status == "miss"
    assert response.result.additional_fields == {
        "request_id": "request-123",
        "future": {"nested": True},
    }
    assert json.loads(response.raw_response.body) == body


@pytest.mark.parametrize(
    ("options", "content_type", "body", "expected"),
    [
        (None, "application/json", b"{}", "json response when binary was requested"),
        (
            CaptureOptions(response_type="json"),
            "image/png",
            b"\x01\x02",
            "binary response when json was requested",
        ),
    ],
)
def test_known_response_types_reject_wrong_success_media_type(
    options: CaptureOptions | None,
    content_type: str,
    body: bytes,
    expected: str,
) -> None:
    def response_factory(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": content_type})

    http_client, _ = _recording_http_client(response_factory)
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        with pytest.raises(ScreenshotScoutResponseDecodingError, match=expected) as captured:
            client.capture("https://example.com", options)
    finally:
        http_client.close()

    assert captured.value.raw_response.body == body
    assert captured.value.cause is captured.value.__cause__


def test_open_response_type_uses_actual_media_type() -> None:
    def response_factory(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"screenshot_url": "https://cdn.example/a.png"},
            headers={"content-type": "application/json"},
        )

    http_client, _ = _recording_http_client(response_factory)
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        response = client.capture(
            "https://example.com",
            CaptureOptions(response_type="future-response"),
        )
    finally:
        http_client.close()

    assert isinstance(response, JsonCaptureResponse)
    assert response.result.screenshot_url == "https://cdn.example/a.png"


@pytest.mark.parametrize("body", [b"{", b"[]", b'{"screenshot_url":123}'])
def test_malformed_successful_json_retains_raw_response(body: bytes) -> None:
    def response_factory(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=body,
            headers={"content-type": "application/json"},
        )

    http_client, _ = _recording_http_client(response_factory)
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        with pytest.raises(ScreenshotScoutResponseDecodingError) as captured:
            client.capture(
                "https://example.com",
                CaptureOptions(response_type="json"),
            )
    finally:
        http_client.close()

    assert captured.value.raw_response.status == 200
    assert captured.value.raw_response.body == body


def test_api_failure_retains_parsed_fields_and_exact_raw_response() -> None:
    error_body = {
        "error_code": "invalid_options",
        "error_message": "One or more options are invalid.",
        "errors": [{"option": "format", "message": "Unsupported."}],
        "request_id": "request-456",
    }
    encoded = json.dumps(error_body, separators=(",", ":")).encode()

    def response_factory(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            content=encoded,
            headers={
                "content-type": "application/json; charset=utf-8",
                "x-request-id": "request-456",
            },
        )

    http_client, _ = _recording_http_client(response_factory)
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        with pytest.raises(ScreenshotScoutAPIError) as captured:
            client.capture("not-semantically-validated")
    finally:
        http_client.close()

    error = captured.value
    assert error.status == 400
    assert error.error_code == "invalid_options"
    assert error.error_message == "One or more options are invalid."
    assert error.errors == error_body["errors"]
    assert error.response_body == error_body
    assert error.raw_response.headers["x-request-id"] == ("request-456",)
    assert error.raw_response.body == encoded


def test_non_json_redirect_failure_is_not_followed_or_retried() -> None:
    calls = 0

    def response_factory(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            302,
            content=b"redirect",
            headers={"location": "https://other.example/v1/capture"},
        )

    http_client, _ = _recording_http_client(response_factory)
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        with pytest.raises(ScreenshotScoutAPIError) as captured:
            client.capture("https://example.com")
    finally:
        http_client.close()

    assert calls == 1
    assert captured.value.status == 302
    assert captured.value.error_code is None
    assert captured.value.response_body is None
    assert captured.value.raw_response.body == b"redirect"


def test_transport_failure_retains_native_cause_and_is_not_retried() -> None:
    native_cause = RuntimeError("socket closed")
    calls = 0

    def response_factory(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise native_cause

    http_client, _ = _recording_http_client(response_factory)
    try:
        client = ScreenshotScoutClient("key", http_client=http_client)
        with pytest.raises(ScreenshotScoutTransportError) as captured:
            client.capture("https://example.com")
    finally:
        http_client.close()

    assert calls == 1
    assert captured.value.cause is native_cause
    assert captured.value.__cause__ is native_cause


def test_custom_base_url_timeout_and_injected_client_lifecycle() -> None:
    http_client, requests = _recording_http_client()
    with http_client:
        with ScreenshotScoutClient(
            "key",
            base_url="https://api.example.test/root/",
            request_timeout=12.5,
            http_client=http_client,
        ) as client:
            client.capture("https://example.com")
        assert not http_client.is_closed

    request = requests[0]
    assert str(request.url) == "https://api.example.test/root/v1/capture"
    timeout = cast(dict[str, float | None], request.extensions["timeout"])
    assert timeout == {
        "connect": 12.5,
        "read": 12.5,
        "write": 12.5,
        "pool": 12.5,
    }
    with pytest.raises(ScreenshotScoutConfigurationError, match="closed"):
        client.capture("https://example.com")


def test_options_are_slotted_and_service_string_values_remain_open() -> None:
    options = CaptureOptions(format="future-format")
    assert not hasattr(options, "__dict__")
    assert options.format == "future-format"
    assert CaptureFormat.WEBP == "webp"
    assert CaptureHTTPMethod.GET.value == "GET"
