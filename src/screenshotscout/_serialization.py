"""Capture option serialization and API-compatible query canonicalization."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, fields
from decimal import Decimal
from typing import TypeAlias

from .errors import ScreenshotScoutSerializationError
from .models import CaptureHTTPMethod, CaptureOptions

WireScalar: TypeAlias = str | int | float | bool
WireJSONValue: TypeAlias = WireScalar | list[str]
WirePair: TypeAlias = tuple[str, str]

_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_REPEATED_OPTIONS = frozenset(
    {
        "cookies",
        "headers",
        "hide_selectors",
        "click_selectors",
        "click_all_selectors",
        "inject_css",
        "inject_js",
    }
)
_FORM_SAFE_BYTES = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789*-._")


@dataclass(frozen=True, slots=True)
class SerializedCaptureOptions:
    pairs: tuple[WirePair, ...]
    body: dict[str, WireJSONValue]


def serialize_capture_options(
    target_url: str,
    options: CaptureOptions | None,
) -> SerializedCaptureOptions:
    """Serialize the target URL and typed options without service validation."""

    if not isinstance(target_url, str):
        raise ScreenshotScoutSerializationError(
            "The capture target URL must be a string.",
            "url",
        )
    if options is not None and not isinstance(options, CaptureOptions):
        raise ScreenshotScoutSerializationError(
            "Capture options must be a CaptureOptions instance when provided."
        )

    pairs: list[WirePair] = [("url", target_url)]
    body: dict[str, WireJSONValue] = {"url": target_url}
    if options is None:
        return SerializedCaptureOptions(tuple(pairs), body)

    for option_field in fields(options):
        option = option_field.name
        value: object = getattr(options, option)
        if value is None:
            continue

        if option in _REPEATED_OPTIONS:
            repeated = _serialize_repeated_value(option, value)
            if not repeated:
                continue
            body[option] = repeated
            pairs.extend((option, item) for item in repeated)
            continue

        pair_value, body_value = _serialize_scalar_value(option, value)
        pairs.append((option, pair_value))
        body[option] = body_value

    return SerializedCaptureOptions(tuple(pairs), body)


def serialize_capture_method(method: CaptureHTTPMethod) -> CaptureHTTPMethod:
    """Validate the SDK-owned closed HTTP method selector."""

    if not isinstance(method, CaptureHTTPMethod):
        raise ScreenshotScoutSerializationError(
            "The capture method must be CaptureHTTPMethod.GET or CaptureHTTPMethod.POST.",
            "method",
        )
    return method


def build_canonical_query(pairs: Sequence[WirePair], access_key: str) -> str:
    """Build the stable canonical query used by Screenshot Scout signing."""

    entries = [*pairs, ("access_key", access_key)]
    entries.sort(key=lambda pair: pair[0])
    return encode_query_pairs(entries)


def encode_query_pairs(pairs: Sequence[WirePair]) -> str:
    """Encode pairs with the WHATWG URLSearchParams form-encoding rules."""

    try:
        return "&".join(
            f"{_form_encode_component(name)}={_form_encode_component(value)}"
            for name, value in pairs
        )
    except UnicodeError as cause:
        error = ScreenshotScoutSerializationError(
            "Capture options contain text that cannot be encoded as UTF-8."
        )
        raise error from cause


def encode_json_body(body: dict[str, WireJSONValue]) -> bytes:
    """Encode a POST body while keeping JSON failures in the serialization category."""

    try:
        text = json.dumps(
            body,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        return text.encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as cause:
        error = ScreenshotScoutSerializationError(
            "The POST capture body could not be serialized as JSON."
        )
        raise error from cause


def _serialize_repeated_value(option: str, value: object) -> list[str]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ScreenshotScoutSerializationError(
            f'The capture option "{option}" must be a sequence of strings.',
            option,
        )

    repeated: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ScreenshotScoutSerializationError(
                f'The capture option "{option}" must contain only strings.',
                option,
            )
        repeated.append(item)
    return repeated


def _serialize_scalar_value(option: str, value: object) -> tuple[str, WireScalar]:
    if isinstance(value, str):
        return value, value
    if isinstance(value, bool):
        return ("true" if value else "false"), value
    if isinstance(value, int):
        if abs(value) > _MAX_SAFE_INTEGER:
            raise ScreenshotScoutSerializationError(
                f'The capture option "{option}" must use a JSON-safe integer.',
                option,
            )
        return str(value), value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ScreenshotScoutSerializationError(
                f'The capture option "{option}" must be a finite number.',
                option,
            )
        return _ecmascript_number_string(value), value

    raise ScreenshotScoutSerializationError(
        f'The capture option "{option}" must be a string, finite number, or boolean.',
        option,
    )


def _ecmascript_number_string(value: float) -> str:
    """Match JavaScript's ordinary finite-number string form used by URLSearchParams."""

    if value == 0:
        return "0"

    absolute = abs(value)
    representation = repr(value).lower()

    if 1e-6 <= absolute < 1e21:
        if "e" in representation:
            representation = format(Decimal(representation), "f")
        if representation.endswith(".0"):
            representation = representation[:-2]
        return representation

    if "e" not in representation:
        representation = format(value, ".15e")
    mantissa, exponent_text = representation.split("e", 1)
    if mantissa.endswith(".0"):
        mantissa = mantissa[:-2]
    exponent = int(exponent_text)
    sign = "+" if exponent >= 0 else ""
    return f"{mantissa}e{sign}{exponent}"


def _form_encode_component(value: str) -> str:
    encoded: list[str] = []
    for byte in value.encode("utf-8"):
        if byte in _FORM_SAFE_BYTES:
            encoded.append(chr(byte))
        elif byte == 0x20:
            encoded.append("+")
        else:
            encoded.append(f"%{byte:02X}")
    return "".join(encoded)
