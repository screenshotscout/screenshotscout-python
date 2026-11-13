"""Blocking and async-I/O Screenshot Scout HTTPX clients."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

import httpx

from ._response import (
    ExpectedResponseKind,
    create_api_error,
    create_raw_response,
    decode_success_response,
)
from ._serialization import (
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
_CAPTURE_PATH = "/v1/capture"
_ACCESS_KEY_PATTERN = re.compile(r"[A-Za-z0-9\-._~+/]+=*")
_ACCESS_KEY_VARIABLE = "SCREENSHOTSCOUT_ACCESS_KEY"
_SECRET_KEY_VARIABLE = "SCREENSHOTSCOUT_SECRET_KEY"
_BASE_URL_VARIABLE = "SCREENSHOTSCOUT_BASE_URL"


@dataclass(frozen=True, slots=True)
class _ClientConfiguration:
    access_key: str = field(repr=False)
    secret_key: str | None = field(repr=False)
    secret_key_from_environment: bool
    capture_endpoint: str
    base_url_from_environment: bool


@dataclass(frozen=True, slots=True)
class _PreparedRequest:
    method: CaptureHTTPMethod
    url: str
    # Hidden from repr() because it carries the access key in the Authorization header.
    headers: Mapping[str, str] = field(repr=False)
    content: bytes | None
    expected_kind: ExpectedResponseKind


class ScreenshotScoutClient:
    """Reusable blocking Screenshot Scout client backed by HTTPX."""

    __slots__ = ("_closed", "_configuration", "_http_client", "_owns_http_client")

    def __init__(
        self,
        access_key: str | None = None,
        *,
        secret_key: str | None = None,
        base_url: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Create a client.

        When no key is passed, the client reads ``SCREENSHOTSCOUT_ACCESS_KEY`` and, if it's set,
        ``SCREENSHOTSCOUT_SECRET_KEY``. Passing either key means neither variable is read.

        ``base_url`` sends requests to another server, such as your own proxy or a mock server.
        Captures go to this URL plus ``/v1/capture``, and ``build_capture_url()`` builds URLs on
        it. It defaults to ``SCREENSHOTSCOUT_BASE_URL``, then to the Screenshot Scout API.
        """

        self._configuration = _build_configuration(
            access_key=access_key,
            secret_key=secret_key,
            base_url=base_url,
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
                timeout=None,
            )
        )
        self._closed = False

    def capture(
        self,
        target_url: str,
        options: CaptureOptions | None = None,
        *,
        method: CaptureHTTPMethod | None = None,
    ) -> CaptureResponse:
        """Capture ``target_url`` and return the buffered binary or JSON response.

        ``method`` defaults to POST, or GET when the client has a secret key, because POST
        requests can't be signed.
        """

        self._ensure_open()
        prepared = _prepare_request(self._configuration, target_url, options, method)
        try:
            response = self._http_client.request(
                prepared.method.value,
                prepared.url,
                headers=prepared.headers,
                content=prepared.content,
                follow_redirects=False,
            )
            body = response.read()
        except Exception as cause:
            error = ScreenshotScoutTransportError(
                _transport_error_message(self._configuration),
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
        access_key: str | None = None,
        *,
        secret_key: str | None = None,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create a client.

        When no key is passed, the client reads ``SCREENSHOTSCOUT_ACCESS_KEY`` and, if it's set,
        ``SCREENSHOTSCOUT_SECRET_KEY``. Passing either key means neither variable is read.

        ``base_url`` sends requests to another server, such as your own proxy or a mock server.
        Captures go to this URL plus ``/v1/capture``, and ``build_capture_url()`` builds URLs on
        it. It defaults to ``SCREENSHOTSCOUT_BASE_URL``, then to the Screenshot Scout API.
        """

        self._configuration = _build_configuration(
            access_key=access_key,
            secret_key=secret_key,
            base_url=base_url,
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
                timeout=None,
            )
        )
        self._closed = False

    async def capture(
        self,
        target_url: str,
        options: CaptureOptions | None = None,
        *,
        method: CaptureHTTPMethod | None = None,
    ) -> CaptureResponse:
        """Await the final inline capture response for ``target_url``.

        ``method`` defaults to POST, or GET when the client has a secret key, because POST
        requests can't be signed.
        """

        self._ensure_open()
        prepared = _prepare_request(self._configuration, target_url, options, method)
        try:
            response = await self._http_client.request(
                prepared.method.value,
                prepared.url,
                headers=prepared.headers,
                content=prepared.content,
                follow_redirects=False,
            )
            body = await response.aread()
        except asyncio.CancelledError:
            raise
        except Exception as cause:
            error = ScreenshotScoutTransportError(
                _transport_error_message(self._configuration),
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
    base_url: object = None,
    environ: Mapping[str, str] = os.environ,
) -> _ClientConfiguration:
    # Keys passed to the client always win: if either one is passed, neither variable is read.
    # Only when both are None are both read from the environment.
    secret_key_from_environment = False
    if access_key is None and secret_key is None:
        access_key = _read_variable(environ, _ACCESS_KEY_VARIABLE)
        secret_key = _read_variable(environ, _SECRET_KEY_VARIABLE)
        if access_key is None:
            raise ScreenshotScoutConfigurationError(
                "A non-blank Screenshot Scout access key is required. "
                f"Pass one, or set {_ACCESS_KEY_VARIABLE}."
            )
        secret_key_from_environment = secret_key is not None

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

    try:
        httpx.Headers({"Authorization": f"Bearer {access_key}"})
    except (TypeError, ValueError) as cause:
        error = ScreenshotScoutConfigurationError(
            "The Screenshot Scout access key cannot be used in an Authorization header."
        )
        raise error from cause

    # Resolved after the keys, so key errors come first.
    capture_endpoint, base_url_from_environment = _resolve_capture_endpoint(base_url, environ)

    return _ClientConfiguration(
        access_key=access_key,
        secret_key=secret_key,
        secret_key_from_environment=secret_key_from_environment,
        capture_endpoint=capture_endpoint,
        base_url_from_environment=base_url_from_environment,
    )


def _read_variable(environ: Mapping[str, str], name: str) -> str | None:
    value = environ.get(name)
    if not value:
        return None
    if not value.strip():
        raise ScreenshotScoutConfigurationError(f"{name} is set but blank.")
    return value


def _resolve_capture_endpoint(base_url: object, environ: Mapping[str, str]) -> tuple[str, bool]:
    # Returns the capture endpoint and whether its base URL came from the environment. A base URL
    # passed to the client wins. Without one, the variable is read, whether or not keys were
    # passed, and without that the Screenshot Scout API is used.
    if base_url is not None and not isinstance(base_url, str):
        raise ScreenshotScoutConfigurationError(
            "The Screenshot Scout base URL must be a string when provided."
        )
    if base_url:
        return _append_capture_path(base_url), False
    environment_base_url = _read_variable(environ, _BASE_URL_VARIABLE)
    if environment_base_url is not None:
        return _append_capture_path(environment_base_url), True
    return _append_capture_path(_DEFAULT_BASE_URL), False


def _append_capture_path(base_url: str) -> str:
    # The base URL is used as given, never parsed: only trailing slashes are removed.
    return base_url.rstrip("/") + _CAPTURE_PATH


def _prepare_request(
    configuration: _ClientConfiguration,
    target_url: str,
    options: CaptureOptions | None,
    method: CaptureHTTPMethod | None,
) -> _PreparedRequest:
    serialized = serialize_capture_options(target_url, options)
    if method is None:
        # Without a method, a client that signs sends GET, because POST requests can't be signed.
        method = (
            CaptureHTTPMethod.POST if configuration.secret_key is None else CaptureHTTPMethod.GET
        )
    capture_method = serialize_capture_method(method)
    if configuration.secret_key is not None and capture_method is CaptureHTTPMethod.POST:
        source = (
            f" from {_SECRET_KEY_VARIABLE}" if configuration.secret_key_from_environment else ""
        )
        raise ScreenshotScoutConfigurationError(
            f"POST requests can't be signed. This client has a secret key{source}: send this "
            "capture with method GET, or use a client without a secret key and an API key that "
            "doesn't require signed requests."
        )
    signature = _create_signature(configuration, serialized.pairs)
    headers: dict[str, str] = {
        "Authorization": f"Bearer {configuration.access_key}",
    }

    if capture_method is CaptureHTTPMethod.GET:
        pairs = list(serialized.pairs)
        if signature is not None:
            pairs.append(("signature", signature))
        query = encode_query_pairs(pairs)
        url = f"{configuration.capture_endpoint}?{query}"
        content = None
    else:
        headers["Content-Type"] = "application/json"
        url = configuration.capture_endpoint
        content = encode_json_body(serialized.body)

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
    return f"{configuration.capture_endpoint}?{encode_query_pairs(pairs)}"


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


def _transport_error_message(configuration: _ClientConfiguration) -> str:
    message = "Screenshot Scout request failed before an HTTP response body was received."
    if configuration.base_url_from_environment:
        message += f" The base URL comes from {_BASE_URL_VARIABLE}."
    return message
