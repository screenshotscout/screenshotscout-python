"""Buffered HTTP response preservation and decoding."""

from __future__ import annotations

import json
from types import MappingProxyType
from typing import Any, Literal, NoReturn, TypeAlias

import httpx

from .errors import ScreenshotScoutAPIError, ScreenshotScoutResponseDecodingError
from .models import (
    BinaryCaptureResponse,
    CaptureResponse,
    CaptureResult,
    JsonCaptureResponse,
    RawResponse,
)

ExpectedResponseKind: TypeAlias = Literal["binary", "json"] | None


def create_raw_response(response: httpx.Response, body: bytes) -> RawResponse:
    """Preserve status, multi-value headers, content type, and exact body bytes."""

    grouped_headers: dict[str, list[str]] = {}
    for name, value in response.headers.multi_items():
        grouped_headers.setdefault(name.lower(), []).append(value)
    headers = MappingProxyType({name: tuple(values) for name, values in grouped_headers.items()})
    return RawResponse(
        status=response.status_code,
        status_text=response.reason_phrase,
        headers=headers,
        content_type=response.headers.get("content-type"),
        body=body,
    )


def create_api_error(raw_response: RawResponse) -> ScreenshotScoutAPIError:
    """Create an API error without making JSON parsing a prerequisite for raw access."""

    parsed, value, _ = _try_parse_json(raw_response.body)
    object_body = value if parsed and isinstance(value, dict) else None
    error_code = _optional_dict_string(object_body, "error_code")
    error_message = _optional_dict_string(object_body, "error_message")
    errors_value = object_body.get("errors") if object_body is not None else None
    errors = errors_value if isinstance(errors_value, list) else None
    return ScreenshotScoutAPIError(
        raw_response=raw_response,
        response_body=value if parsed else None,
        error_code=error_code,
        error_message=error_message,
        errors=errors,
    )


def decode_success_response(
    raw_response: RawResponse,
    expected_kind: ExpectedResponseKind,
) -> CaptureResponse:
    """Decode a success according to its media type and the requested representation."""

    actual_kind: Literal["binary", "json"] = (
        "json" if _is_json_media_type(raw_response.content_type) else "binary"
    )
    if expected_kind is not None and actual_kind != expected_kind:
        cause = TypeError(f"Expected a {expected_kind} response but received {actual_kind}.")
        _raise_decoding_error(
            (
                "Screenshot Scout returned a successful "
                f"{actual_kind} response when {expected_kind} was requested."
            ),
            raw_response,
            cause,
        )

    if actual_kind == "json":
        return _decode_json_response(raw_response)
    return _decode_binary_response(raw_response)


def _decode_binary_response(raw_response: RawResponse) -> BinaryCaptureResponse:
    return BinaryCaptureResponse(
        bytes=raw_response.body,
        screenshot_url=_first_header(raw_response, "screenshot-scout-screenshot-url"),
        screenshot_url_expires_at=_first_header(
            raw_response,
            "screenshot-scout-screenshot-url-expires-at",
        ),
        cache_status=_first_header(raw_response, "screenshot-scout-cache-status"),
        raw_response=raw_response,
    )


def _decode_json_response(raw_response: RawResponse) -> JsonCaptureResponse:
    parsed, value, cause = _try_parse_json(raw_response.body)
    if not parsed:
        assert cause is not None
        _raise_decoding_error(
            "Screenshot Scout returned a successful JSON response that could not be decoded.",
            raw_response,
            cause,
        )
    if not isinstance(value, dict):
        _raise_decoding_error(
            "Screenshot Scout returned a successful JSON response that was not an object.",
            raw_response,
            TypeError("Expected a JSON object."),
        )

    screenshot_url = _read_optional_string(value, "screenshot_url", raw_response)
    screenshot_url_expires_at = _read_optional_string(
        value,
        "screenshot_url_expires_at",
        raw_response,
    )
    cache_status = _read_optional_string(value, "cache_status", raw_response)
    known_keys = {
        "screenshot_url",
        "screenshot_url_expires_at",
        "cache_status",
    }
    additional_fields = MappingProxyType(
        {key: field_value for key, field_value in value.items() if key not in known_keys}
    )
    result = CaptureResult(
        screenshot_url=screenshot_url,
        screenshot_url_expires_at=screenshot_url_expires_at,
        cache_status=cache_status,
        additional_fields=additional_fields,
    )
    return JsonCaptureResponse(result=result, raw_response=raw_response)


def _read_optional_string(
    value: dict[str, Any],
    key: str,
    raw_response: RawResponse,
) -> str | None:
    if key not in value:
        return None
    field_value = value[key]
    if not isinstance(field_value, str):
        _raise_decoding_error(
            f'Screenshot Scout returned a non-string "{key}" JSON field.',
            raw_response,
            TypeError(f'Expected "{key}" to be a string.'),
        )
    return field_value


def _first_header(raw_response: RawResponse, name: str) -> str | None:
    values = raw_response.headers.get(name)
    return values[0] if values else None


def _is_json_media_type(content_type: str | None) -> bool:
    if content_type is None:
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")


def _try_parse_json(body: bytes) -> tuple[bool, Any, Exception | None]:
    try:
        value: Any = json.loads(body)
        return True, value, None
    except (UnicodeDecodeError, json.JSONDecodeError) as cause:
        return False, None, cause


def _optional_dict_string(value: dict[str, Any] | None, key: str) -> str | None:
    if value is None:
        return None
    field_value = value.get(key)
    return field_value if isinstance(field_value, str) else None


def _raise_decoding_error(
    message: str,
    raw_response: RawResponse,
    cause: Exception,
) -> NoReturn:
    error = ScreenshotScoutResponseDecodingError(message, raw_response, cause)
    raise error from cause
