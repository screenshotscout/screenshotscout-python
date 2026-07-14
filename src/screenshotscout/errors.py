"""Screenshot Scout SDK error categories."""

from __future__ import annotations

from typing import Any

from .models import RawResponse


class ScreenshotScoutError(Exception):
    """Base class for all SDK-defined errors."""


class ScreenshotScoutConfigurationError(ScreenshotScoutError):
    """The client configuration is missing or unusable."""


class ScreenshotScoutSerializationError(ScreenshotScoutError):
    """A request value cannot be represented safely on the wire."""

    option: str | None

    def __init__(self, message: str, option: str | None = None) -> None:
        super().__init__(message)
        self.option = option


class ScreenshotScoutTransportError(ScreenshotScoutError):
    """The request failed before a complete HTTP response was received."""

    cause: Exception

    def __init__(self, message: str, cause: Exception) -> None:
        super().__init__(message)
        self.cause = cause


class ScreenshotScoutAPIError(ScreenshotScoutError):
    """Screenshot Scout returned a non-success HTTP response."""

    status: int
    error_code: str | None
    error_message: str | None
    errors: list[Any] | None
    response_body: Any | None
    raw_response: RawResponse

    def __init__(
        self,
        *,
        raw_response: RawResponse,
        response_body: Any | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        errors: list[Any] | None = None,
    ) -> None:
        super().__init__(
            error_message
            or f"Screenshot Scout API request failed with status {raw_response.status}."
        )
        self.status = raw_response.status
        self.error_code = error_code
        self.error_message = error_message
        self.errors = errors
        self.response_body = response_body
        self.raw_response = raw_response


class ScreenshotScoutResponseDecodingError(ScreenshotScoutError):
    """A successful response could not be decoded as the requested representation."""

    raw_response: RawResponse
    cause: Exception | None

    def __init__(
        self,
        message: str,
        raw_response: RawResponse,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.cause = cause
