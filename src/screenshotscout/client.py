"""Blocking and async-I/O Screenshot Scout HTTPX clients."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import TracebackType
from typing import Self, TypeAlias, cast

import httpx

from ._response import (
    ExpectedResponseKind,
    create_api_error,
    create_raw_response,
    decode_success_response,
)
from ._serialization import (
    WireJSONValue,
    WirePair,
    build_canonical_query,
    encode_json_body,
    encode_query_pairs,
    serialize_capture_method,
    serialize_capture_options,
)
from .errors import (
    ScreenshotScoutConfigurationError,
    ScreenshotScoutSerializationError,
    ScreenshotScoutTransportError,
)
from .models import CaptureHTTPMethod, CaptureOptions, CaptureResponse

_DEFAULT_BASE_URL = "https://api.screenshotscout.com"
_ACCESS_KEY_PATTERN = re.compile(r"[A-Za-z0-9\-._~+/]+=*")
RequestTimeout: TypeAlias = float | httpx.Timeout | None


class _RequestTimeoutDefault:
    __slots__ = ()

    def __repr__(self) -> str:
        return "<default>"


_REQUEST_TIMEOUT_UNSET = _RequestTimeoutDefault()
_REQUEST_TIMEOUT_DEFAULT = cast(RequestTimeout, _REQUEST_TIMEOUT_UNSET)


@dataclass(frozen=True, slots=True)
class _ClientConfiguration:
    access_key: str
    secret_key: str | None
    endpoint: str
    request_timeout: RequestTimeout
    use_client_default_timeout: bool


@dataclass(frozen=True, slots=True)
class _PreparedRequest:
    method: CaptureHTTPMethod
    url: str
    headers: Mapping[str, str]
    content: bytes | None
    expected_kind: ExpectedResponseKind


class ScreenshotScoutClient:
    """Reusable blocking Screenshot Scout client backed by HTTPX."""

    __slots__ = ("_closed", "_configuration", "_http_client", "_owns_http_client")

    def __init__(
        self,
        access_key: str,
        *,
        secret_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        request_timeout: RequestTimeout = _REQUEST_TIMEOUT_DEFAULT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._configuration = _build_configuration(
            access_key=access_key,
            secret_key=secret_key,
            base_url=base_url,
            request_timeout=request_timeout,
        )
        if http_client is not None and not isinstance(http_client, httpx.Client):
            raise ScreenshotScoutConfigurationError(
                "http_client must be an httpx.Client when provided."
            )
        self._owns_http_client = http_client is None
        self._http_client = (
            http_client
            if http_client is not None
            else httpx.Client(
                follow_redirects=False,
                timeout=self._configuration.request_timeout,
            )
        )
        self._closed = False

    def capture(
        self,
        target_url: str,
        options: CaptureOptions | None = None,
        *,
        method: CaptureHTTPMethod = CaptureHTTPMethod.POST,
    ) -> CaptureResponse:
        """Capture ``target_url`` and return the buffered binary or JSON response."""

        self._ensure_open()
        prepared = _prepare_request(self._configuration, target_url, options, method)
        httpx_request_timeout = (
            httpx.USE_CLIENT_DEFAULT
            if self._configuration.use_client_default_timeout
            else self._configuration.request_timeout
        )
        try:
            response = self._http_client.request(
                prepared.method.value,
                prepared.url,
                headers=prepared.headers,
                content=prepared.content,
                follow_redirects=False,
                timeout=httpx_request_timeout,
            )
            body = response.read()
        except Exception as cause:
            error = ScreenshotScoutTransportError(
                "Screenshot Scout request failed before an HTTP response body was received.",
                cause,
            )
            raise error from cause

        raw_response = create_raw_response(response, body)
        if not 200 <= raw_response.status <= 299:
            raise create_api_error(raw_response)
        return decode_success_response(raw_response, prepared.expected_kind)

    def build_capture_url(
        self,
        target_url: str,
        options: CaptureOptions | None = None,
    ) -> str:
        """Build a sensitive GET capture URL without making an HTTP request."""

        return _build_capture_url(self._configuration, target_url, options)

    def close(self) -> None:
        """Close transport resources owned by this SDK client."""

        if self._closed:
            return
        try:
            if self._owns_http_client:
                self._http_client.close()
        finally:
            self._closed = True

    def __enter__(self) -> Self:
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise ScreenshotScoutConfigurationError("This ScreenshotScoutClient is closed.")


class AsyncScreenshotScoutClient:
    """Reusable async-I/O client that waits for inline Screenshot Scout responses."""

    __slots__ = ("_closed", "_configuration", "_http_client", "_owns_http_client")

    def __init__(
        self,
        access_key: str,
        *,
        secret_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        request_timeout: RequestTimeout = _REQUEST_TIMEOUT_DEFAULT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._configuration = _build_configuration(
            access_key=access_key,
            secret_key=secret_key,
            base_url=base_url,
            request_timeout=request_timeout,
        )
        if http_client is not None and not isinstance(http_client, httpx.AsyncClient):
            raise ScreenshotScoutConfigurationError(
                "http_client must be an httpx.AsyncClient when provided."
            )
        self._owns_http_client = http_client is None
        self._http_client = (
            http_client
            if http_client is not None
            else httpx.AsyncClient(
                follow_redirects=False,
                timeout=self._configuration.request_timeout,
            )
        )
        self._closed = False

    async def capture(
        self,
        target_url: str,
        options: CaptureOptions | None = None,
        *,
        method: CaptureHTTPMethod = CaptureHTTPMethod.POST,
    ) -> CaptureResponse:
        """Await the final inline capture response for ``target_url``."""

        self._ensure_open()
        prepared = _prepare_request(self._configuration, target_url, options, method)
        httpx_request_timeout = (
            httpx.USE_CLIENT_DEFAULT
            if self._configuration.use_client_default_timeout
            else self._configuration.request_timeout
        )
        try:
            response = await self._http_client.request(
                prepared.method.value,
                prepared.url,
                headers=prepared.headers,
                content=prepared.content,
                follow_redirects=False,
                timeout=httpx_request_timeout,
            )
            body = await response.aread()
        except asyncio.CancelledError:
            raise
        except Exception as cause:
            error = ScreenshotScoutTransportError(
                "Screenshot Scout request failed before an HTTP response body was received.",
                cause,
            )
            raise error from cause

        raw_response = create_raw_response(response, body)
        if not 200 <= raw_response.status <= 299:
            raise create_api_error(raw_response)
        return decode_success_response(raw_response, prepared.expected_kind)

    def build_capture_url(
        self,
        target_url: str,
        options: CaptureOptions | None = None,
    ) -> str:
        """Build a sensitive GET capture URL without making an HTTP request."""

        return _build_capture_url(self._configuration, target_url, options)

    async def aclose(self) -> None:
        """Close transport resources owned by this SDK client."""

        if self._closed:
            return
        try:
            if self._owns_http_client:
                await self._http_client.aclose()
        finally:
            self._closed = True

    async def __aenter__(self) -> Self:
        self._ensure_open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    def _ensure_open(self) -> None:
        if self._closed:
            raise ScreenshotScoutConfigurationError("This AsyncScreenshotScoutClient is closed.")


def _build_configuration(
    *,
    access_key: object,
    secret_key: object,
    base_url: object,
    request_timeout: object,
) -> _ClientConfiguration:
    if not isinstance(access_key, str) or not access_key.strip():
        raise ScreenshotScoutConfigurationError(
            "A non-blank Screenshot Scout access key is required."
        )
    if _ACCESS_KEY_PATTERN.fullmatch(access_key) is None:
        raise ScreenshotScoutConfigurationError(
            "The Screenshot Scout access key is not a valid Bearer credential."
        )
    if secret_key is not None and (not isinstance(secret_key, str) or not secret_key.strip()):
        raise ScreenshotScoutConfigurationError(
            "The Screenshot Scout secret key must be a non-blank string when provided."
        )

    endpoint = _capture_endpoint(base_url)
    if request_timeout is _REQUEST_TIMEOUT_UNSET:
        timeout = None
        use_client_default_timeout = True
    else:
        timeout = _validate_request_timeout(request_timeout)
        use_client_default_timeout = False
    try:
        httpx.Headers({"Authorization": f"Bearer {access_key}"})
    except (TypeError, ValueError) as cause:
        error = ScreenshotScoutConfigurationError(
            "The Screenshot Scout access key cannot be used in an Authorization header."
        )
        raise error from cause

    return _ClientConfiguration(
        access_key=access_key,
        secret_key=secret_key,
        endpoint=endpoint,
        request_timeout=timeout,
        use_client_default_timeout=use_client_default_timeout,
    )


def _capture_endpoint(base_url: object) -> str:
    if not isinstance(base_url, str) or not base_url or base_url.strip() != base_url:
        raise ScreenshotScoutConfigurationError(
            "base_url must be a non-blank absolute HTTP or HTTPS URL."
        )
    try:
        parsed = httpx.URL(base_url)
    except (TypeError, httpx.InvalidURL) as cause:
        error = ScreenshotScoutConfigurationError(
            "base_url must be a non-blank absolute HTTP or HTTPS URL."
        )
        raise error from cause
    if parsed.scheme not in {"http", "https"} or parsed.host is None:
        raise ScreenshotScoutConfigurationError(
            "base_url must be a non-blank absolute HTTP or HTTPS URL."
        )
    if parsed.query or parsed.fragment:
        raise ScreenshotScoutConfigurationError(
            "base_url must not contain a query string or fragment."
        )

    base_path = parsed.path.rstrip("/")
    endpoint = parsed.copy_with(path=f"{base_path}/v1/capture")
    return str(endpoint)


def _validate_request_timeout(value: object) -> RequestTimeout:
    if value is None:
        return None
    if isinstance(value, httpx.Timeout):
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScreenshotScoutConfigurationError(
            "request_timeout must be a positive number, httpx.Timeout, or None."
        )
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ScreenshotScoutConfigurationError(
            "request_timeout must be a positive number, httpx.Timeout, or None."
        )
    return timeout


def _prepare_request(
    configuration: _ClientConfiguration,
    target_url: str,
    options: CaptureOptions | None,
    method: CaptureHTTPMethod,
) -> _PreparedRequest:
    serialized = serialize_capture_options(target_url, options)
    capture_method = serialize_capture_method(method)
    signature = _create_signature(configuration, serialized.pairs)
    headers: dict[str, str] = {
        "Authorization": f"Bearer {configuration.access_key}",
    }

    if capture_method is CaptureHTTPMethod.GET:
        pairs = list(serialized.pairs)
        if signature is not None:
            pairs.append(("signature", signature))
        query = encode_query_pairs(pairs)
        url = f"{configuration.endpoint}?{query}"
        content = None
    else:
        headers["Content-Type"] = "application/json"
        body: dict[str, WireJSONValue] = dict(serialized.body)
        if signature is not None:
            body["signature"] = signature
        url = configuration.endpoint
        content = encode_json_body(body)

    return _PreparedRequest(
        method=capture_method,
        url=url,
        headers=headers,
        content=content,
        expected_kind=_expected_response_kind(options),
    )


def _build_capture_url(
    configuration: _ClientConfiguration,
    target_url: str,
    options: CaptureOptions | None,
) -> str:
    serialized = serialize_capture_options(target_url, options)
    signature = _create_signature(configuration, serialized.pairs)
    pairs: list[WirePair] = [
        ("access_key", configuration.access_key),
        *serialized.pairs,
    ]
    if signature is not None:
        pairs.append(("signature", signature))
    return f"{configuration.endpoint}?{encode_query_pairs(pairs)}"


def _create_signature(
    configuration: _ClientConfiguration,
    pairs: tuple[WirePair, ...],
) -> str | None:
    if configuration.secret_key is None:
        return None
    try:
        canonical_query = build_canonical_query(pairs, configuration.access_key)
        return hmac.new(
            configuration.secret_key.encode("utf-8"),
            canonical_query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    except (UnicodeError, ValueError) as cause:
        error = ScreenshotScoutSerializationError("The capture request could not be signed.")
        raise error from cause


def _expected_response_kind(options: CaptureOptions | None) -> ExpectedResponseKind:
    response_type = options.response_type if options is not None else None
    if response_type is None or response_type == "binary":
        return "binary"
    if response_type == "json":
        return "json"
    return None
