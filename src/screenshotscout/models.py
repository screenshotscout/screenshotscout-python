"""Public values, options, and response models for Screenshot Scout."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Final, Literal, TypeAlias


class CaptureHTTPMethod(StrEnum):
    """Closed selector for the HTTP method used by :meth:`capture`."""

    GET = "GET"
    POST = "POST"


class CaptureFormat:
    """Documented capture format values; raw strings remain supported."""

    GIF: Final[str] = "gif"
    JPEG: Final[str] = "jpeg"
    JPG: Final[str] = "jpg"
    PDF: Final[str] = "pdf"
    PNG: Final[str] = "png"
    TIFF: Final[str] = "tiff"
    WEBP: Final[str] = "webp"


class CaptureResponseType:
    """Documented response type values; raw strings remain supported."""

    BINARY: Final[str] = "binary"
    JSON: Final[str] = "json"


class CaptureWaitUntil:
    """Documented navigation completion values; raw strings remain supported."""

    DOM_CONTENT_LOADED: Final[str] = "domcontentloaded"
    LOAD: Final[str] = "load"
    NETWORK_IDLE_0: Final[str] = "networkidle0"
    NETWORK_IDLE_2: Final[str] = "networkidle2"


class CaptureMediaType:
    """Documented CSS media values; raw strings remain supported."""

    PRINT: Final[str] = "print"
    SCREEN: Final[str] = "screen"


class CaptureColorScheme:
    """Documented color scheme values; raw strings remain supported."""

    AUTO: Final[str] = "auto"
    DARK: Final[str] = "dark"
    LIGHT: Final[str] = "light"


class CaptureImageMode:
    """Documented image resize modes; raw strings remain supported."""

    FILL: Final[str] = "fill"
    FIT: Final[str] = "fit"
    STRETCH: Final[str] = "stretch"


class CaptureImageAnchor:
    """Documented image anchor values; raw strings remain supported."""

    BOTTOM: Final[str] = "bottom"
    BOTTOM_LEFT: Final[str] = "bottom_left"
    BOTTOM_RIGHT: Final[str] = "bottom_right"
    CENTER: Final[str] = "center"
    LEFT: Final[str] = "left"
    RIGHT: Final[str] = "right"
    TOP: Final[str] = "top"
    TOP_LEFT: Final[str] = "top_left"
    TOP_RIGHT: Final[str] = "top_right"


class CapturePdfPaperFormat:
    """Documented PDF paper formats; raw strings remain supported."""

    A3: Final[str] = "a3"
    A4: Final[str] = "a4"
    CONTENT: Final[str] = "content"
    LEGAL: Final[str] = "legal"
    LETTER: Final[str] = "letter"
    TABLOID: Final[str] = "tabloid"


class CaptureStorageMode:
    """Documented storage modes; raw strings remain supported."""

    EXTERNAL: Final[str] = "external"
    MANAGED: Final[str] = "managed"


@dataclass(slots=True, kw_only=True)
class CaptureOptions:
    """Typed Screenshot Scout service options.

    ``url``, ``access_key``, and ``signature`` are deliberately not capture options.
    Values are sent without service-semantic validation or normalization.
    """

    # Target and output
    format: str | None = None
    response_type: str | None = None

    # Network and location
    country: str | None = None
    proxy: str | None = None
    geolocation_latitude: float | None = None
    geolocation_longitude: float | None = None
    geolocation_accuracy: float | None = None

    # Cookies and webpage request headers
    cookies: Sequence[str] | None = None
    headers: Sequence[str] | None = None

    # Navigation and service-side timing
    timeout: int | None = None
    wait_until: str | None = None
    navigation_timeout: int | None = None
    delay: int | None = None

    # Viewport and device emulation
    device: str | None = None
    device_viewport_width: int | None = None
    device_viewport_height: int | None = None
    device_scale_factor: float | None = None
    device_is_mobile: bool | None = None
    device_has_touch: bool | None = None
    device_user_agent: str | None = None

    # Page behavior and preferences
    timezone: str | None = None
    media_type: str | None = None
    color_scheme: str | None = None
    reduced_motion: bool | None = None

    # Full-page capture and pre-scroll behavior
    full_page: bool | None = None
    full_page_pre_scroll: bool | None = None
    full_page_pre_scroll_step: int | None = None
    full_page_pre_scroll_step_delay: int | None = None
    full_page_max_height: int | None = None

    # Blocking
    block_cookie_banners: bool | None = None
    block_ads: bool | None = None
    block_chat_widgets: bool | None = None

    # DOM interactions and injections
    hide_selectors: Sequence[str] | None = None
    click_selectors: Sequence[str] | None = None
    click_all_selectors: Sequence[str] | None = None
    inject_css: Sequence[str] | None = None
    inject_js: Sequence[str] | None = None
    bypass_csp: bool | None = None

    # Framing and selection
    selector: str | None = None
    clip_x: int | None = None
    clip_y: int | None = None
    clip_width: int | None = None
    clip_height: int | None = None

    # Image resizing and quality
    image_width: int | None = None
    image_height: int | None = None
    image_mode: str | None = None
    image_anchor: str | None = None
    image_allow_upscale: bool | None = None
    image_background: str | None = None
    image_quality: int | None = None

    # PDF
    pdf_paper_format: str | None = None
    pdf_landscape: bool | None = None
    pdf_print_background: bool | None = None
    pdf_margin: str | None = None
    pdf_margin_top: str | None = None
    pdf_margin_right: str | None = None
    pdf_margin_bottom: str | None = None
    pdf_margin_left: str | None = None
    pdf_scale: float | None = None

    # Caching
    cache: bool | None = None
    cache_ttl: int | None = None
    cache_key: str | None = None

    # Storage
    storage_mode: str | None = None
    storage_endpoint: str | None = None
    storage_bucket: str | None = None
    storage_region: str | None = None
    storage_object_key: str | None = None


@dataclass(frozen=True, slots=True)
class RawResponse:
    """Exact buffered HTTP response data retained by the SDK."""

    status: int
    status_text: str
    headers: Mapping[str, tuple[str, ...]]
    content_type: str | None
    body: bytes


def _empty_additional_fields() -> Mapping[str, Any]:
    return MappingProxyType({})


@dataclass(frozen=True, slots=True)
class CaptureResult:
    """Documented JSON result metadata plus unrecognized service fields."""

    screenshot_url: str | None = None
    screenshot_url_expires_at: str | None = None
    cache_status: str | None = None
    additional_fields: Mapping[str, Any] = field(default_factory=_empty_additional_fields)


@dataclass(frozen=True, slots=True)
class BinaryCaptureResponse:
    """Buffered binary capture response."""

    bytes: bytes
    raw_response: RawResponse
    screenshot_url: str | None = None
    screenshot_url_expires_at: str | None = None
    cache_status: str | None = None
    kind: Literal["binary"] = field(default="binary", init=False)


@dataclass(frozen=True, slots=True)
class JsonCaptureResponse:
    """Decoded JSON capture response."""

    result: CaptureResult
    raw_response: RawResponse
    kind: Literal["json"] = field(default="json", init=False)


CaptureResponse: TypeAlias = BinaryCaptureResponse | JsonCaptureResponse
