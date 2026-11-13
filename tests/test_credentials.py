from __future__ import annotations

from collections.abc import Iterator, Mapping

import pytest

from screenshotscout import ScreenshotScoutConfigurationError
from screenshotscout.client import _build_configuration, _ClientConfiguration

_MISSING_ACCESS_KEY = "A non-blank Screenshot Scout access key is required."
_MISSING_ACCESS_KEY_VARIABLE = (
    "A non-blank Screenshot Scout access key is required. Pass one, or set "
    "SCREENSHOTSCOUT_ACCESS_KEY."
)
_BASE_URL_NOT_A_STRING = "The Screenshot Scout base URL must be a string when provided."
_DEFAULT_CAPTURE_ENDPOINT = "https://api.screenshotscout.com/v1/capture"
_BOTH_VARIABLES = {
    "SCREENSHOTSCOUT_ACCESS_KEY": "ak_env",
    "SCREENSHOTSCOUT_SECRET_KEY": "sk_env",
}


class _RecordingEnvironment(Mapping[str, str]):
    """A dict-backed environment that records every variable name looked up in it."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = dict(values)
        self.names: list[str] = []

    def __getitem__(self, name: str) -> str:
        self.names.append(name)
        return self._values[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)


def test_with_no_keys_passed_both_key_variables_are_read() -> None:
    configuration = _build_configuration(
        access_key=None,
        secret_key=None,
        environ={"SCREENSHOTSCOUT_ACCESS_KEY": "ak", "SCREENSHOTSCOUT_SECRET_KEY": "sk"},
    )

    assert configuration == _ClientConfiguration(
        access_key="ak",
        secret_key="sk",
        secret_key_from_environment=True,
        capture_endpoint=_DEFAULT_CAPTURE_ENDPOINT,
        base_url_from_environment=False,
    )


@pytest.mark.parametrize(
    "environ",
    [
        {"SCREENSHOTSCOUT_ACCESS_KEY": "ak"},
        {"SCREENSHOTSCOUT_ACCESS_KEY": "ak", "SCREENSHOTSCOUT_SECRET_KEY": ""},
    ],
)
def test_an_unset_or_empty_secret_variable_means_no_secret_key(environ: dict[str, str]) -> None:
    configuration = _build_configuration(access_key=None, secret_key=None, environ=environ)

    assert configuration == _ClientConfiguration(
        access_key="ak",
        secret_key=None,
        secret_key_from_environment=False,
        capture_endpoint=_DEFAULT_CAPTURE_ENDPOINT,
        base_url_from_environment=False,
    )


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {"SCREENSHOTSCOUT_ACCESS_KEY": ""},
        {"SCREENSHOTSCOUT_SECRET_KEY": "sk"},
    ],
)
def test_a_missing_or_empty_access_key_variable_is_an_error_that_names_it(
    environ: dict[str, str],
) -> None:
    with pytest.raises(ScreenshotScoutConfigurationError) as captured:
        _build_configuration(access_key=None, secret_key=None, environ=environ)

    assert str(captured.value) == _MISSING_ACCESS_KEY_VARIABLE


@pytest.mark.parametrize(
    ("environ", "message"),
    [
        ({"SCREENSHOTSCOUT_ACCESS_KEY": "  "}, "SCREENSHOTSCOUT_ACCESS_KEY is set but blank."),
        (
            {"SCREENSHOTSCOUT_ACCESS_KEY": "ak", "SCREENSHOTSCOUT_SECRET_KEY": " \t"},
            "SCREENSHOTSCOUT_SECRET_KEY is set but blank.",
        ),
        ({"SCREENSHOTSCOUT_SECRET_KEY": " "}, "SCREENSHOTSCOUT_SECRET_KEY is set but blank."),
        (
            {"SCREENSHOTSCOUT_ACCESS_KEY": "ak", "SCREENSHOTSCOUT_BASE_URL": " \t"},
            "SCREENSHOTSCOUT_BASE_URL is set but blank.",
        ),
    ],
)
def test_a_whitespace_only_variable_is_an_error_that_names_it(
    environ: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ScreenshotScoutConfigurationError) as captured:
        _build_configuration(access_key=None, secret_key=None, environ=environ)

    assert str(captured.value) == message


def test_a_key_from_the_environment_gets_the_usual_checks() -> None:
    with pytest.raises(ScreenshotScoutConfigurationError) as captured:
        _build_configuration(
            access_key=None,
            secret_key=None,
            environ={"SCREENSHOTSCOUT_ACCESS_KEY": "key with spaces"},
        )

    assert (
        str(captured.value) == "The Screenshot Scout access key is not a valid Bearer credential."
    )


@pytest.mark.parametrize(("access_key", "secret_key"), [("ak", None), ("ak", "sk")])
def test_passing_either_key_means_no_key_variable_is_read(
    access_key: str,
    secret_key: str | None,
) -> None:
    environ = _RecordingEnvironment(_BOTH_VARIABLES)

    configuration = _build_configuration(
        access_key=access_key,
        secret_key=secret_key,
        environ=environ,
    )

    assert configuration == _ClientConfiguration(
        access_key=access_key,
        secret_key=secret_key,
        secret_key_from_environment=False,
        capture_endpoint=_DEFAULT_CAPTURE_ENDPOINT,
        base_url_from_environment=False,
    )
    assert environ.names == ["SCREENSHOTSCOUT_BASE_URL"]


@pytest.mark.parametrize(
    ("access_key", "secret_key"),
    [(None, "sk"), (None, ""), ("", None), ("  ", "sk")],
)
def test_passed_keys_without_a_usable_access_key_keep_the_existing_message(
    access_key: str | None,
    secret_key: str | None,
) -> None:
    environ = _RecordingEnvironment(_BOTH_VARIABLES)

    with pytest.raises(ScreenshotScoutConfigurationError) as captured:
        _build_configuration(access_key=access_key, secret_key=secret_key, environ=environ)

    assert str(captured.value) == _MISSING_ACCESS_KEY
    assert environ.names == []


def test_key_errors_come_before_base_url_errors() -> None:
    with pytest.raises(ScreenshotScoutConfigurationError) as from_environment:
        _build_configuration(
            access_key=None,
            secret_key=None,
            environ={"SCREENSHOTSCOUT_BASE_URL": " "},
        )
    with pytest.raises(ScreenshotScoutConfigurationError) as passed:
        _build_configuration(access_key=" ", secret_key=None, base_url=0, environ={})

    assert str(from_environment.value) == _MISSING_ACCESS_KEY_VARIABLE
    assert str(passed.value) == _MISSING_ACCESS_KEY


@pytest.mark.parametrize(
    ("base_url", "capture_endpoint"),
    [
        ("http://localhost:8787", "http://localhost:8787/v1/capture"),
        ("http://localhost:8787/", "http://localhost:8787/v1/capture"),
        (
            "https://proxy.example.com/screenshotscout/",
            "https://proxy.example.com/screenshotscout/v1/capture",
        ),
        (
            "https://proxy.example.com/screenshotscout//",
            "https://proxy.example.com/screenshotscout/v1/capture",
        ),
        ("https://proxy.example.com/a%20b", "https://proxy.example.com/a%20b/v1/capture"),
    ],
)
def test_a_base_url_is_used_as_given_without_trailing_slashes_and_no_variable_is_read(
    base_url: str,
    capture_endpoint: str,
) -> None:
    environ = _RecordingEnvironment(
        {**_BOTH_VARIABLES, "SCREENSHOTSCOUT_BASE_URL": "http://env.example"}
    )

    configuration = _build_configuration(
        access_key="ak",
        secret_key=None,
        base_url=base_url,
        environ=environ,
    )

    assert configuration == _ClientConfiguration(
        access_key="ak",
        secret_key=None,
        secret_key_from_environment=False,
        capture_endpoint=capture_endpoint,
        base_url_from_environment=False,
    )
    assert environ.names == []


@pytest.mark.parametrize("base_url", [None, ""])
def test_without_a_base_url_the_variable_is_read_even_with_keys_passed(
    base_url: str | None,
) -> None:
    environ = _RecordingEnvironment(
        {**_BOTH_VARIABLES, "SCREENSHOTSCOUT_BASE_URL": "http://localhost:8787/"}
    )

    configuration = _build_configuration(
        access_key="ak",
        secret_key="sk",
        base_url=base_url,
        environ=environ,
    )

    assert configuration == _ClientConfiguration(
        access_key="ak",
        secret_key="sk",
        secret_key_from_environment=False,
        capture_endpoint="http://localhost:8787/v1/capture",
        base_url_from_environment=True,
    )
    assert environ.names == ["SCREENSHOTSCOUT_BASE_URL"]


def test_the_base_url_variable_is_read_after_the_key_variables() -> None:
    environ = _RecordingEnvironment(
        {**_BOTH_VARIABLES, "SCREENSHOTSCOUT_BASE_URL": "http://localhost:8787"}
    )

    configuration = _build_configuration(access_key=None, secret_key=None, environ=environ)

    assert configuration == _ClientConfiguration(
        access_key="ak_env",
        secret_key="sk_env",
        secret_key_from_environment=True,
        capture_endpoint="http://localhost:8787/v1/capture",
        base_url_from_environment=True,
    )
    assert environ.names == [
        "SCREENSHOTSCOUT_ACCESS_KEY",
        "SCREENSHOTSCOUT_SECRET_KEY",
        "SCREENSHOTSCOUT_BASE_URL",
    ]


@pytest.mark.parametrize("environ", [{}, {"SCREENSHOTSCOUT_BASE_URL": ""}])
def test_an_unset_or_empty_base_url_variable_means_the_screenshot_scout_api(
    environ: dict[str, str],
) -> None:
    configuration = _build_configuration(access_key="ak", secret_key=None, environ=environ)

    assert configuration.capture_endpoint == _DEFAULT_CAPTURE_ENDPOINT
    assert configuration.base_url_from_environment is False


@pytest.mark.parametrize(
    ("base_url", "environ", "message"),
    [
        (None, {"SCREENSHOTSCOUT_BASE_URL": "  "}, "SCREENSHOTSCOUT_BASE_URL is set but blank."),
        (0, {"SCREENSHOTSCOUT_BASE_URL": "http://localhost:8787"}, _BASE_URL_NOT_A_STRING),
        (b"http://localhost:8787", {}, _BASE_URL_NOT_A_STRING),
    ],
)
def test_a_blank_base_url_variable_or_a_base_url_that_is_not_a_string_is_an_error(
    base_url: object,
    environ: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ScreenshotScoutConfigurationError) as captured:
        _build_configuration(access_key="ak", secret_key=None, base_url=base_url, environ=environ)

    assert str(captured.value) == message
