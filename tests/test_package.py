from inspect import signature


def test_package_is_importable() -> None:
    import screenshotscout

    assert screenshotscout.__name__ == "screenshotscout"


def test_client_configuration_surface_is_fixed() -> None:
    import screenshotscout

    assert tuple(signature(screenshotscout.ScreenshotScoutClient).parameters) == (
        "access_key",
        "secret_key",
        "base_url",
        "http_client",
    )
    assert tuple(signature(screenshotscout.AsyncScreenshotScoutClient).parameters) == (
        "access_key",
        "secret_key",
        "base_url",
        "http_client",
    )
    for client_class in (
        screenshotscout.ScreenshotScoutClient,
        screenshotscout.AsyncScreenshotScoutClient,
    ):
        assert signature(client_class).parameters["access_key"].default is None
    assert "RequestTimeout" not in screenshotscout.__all__
    assert not hasattr(screenshotscout, "RequestTimeout")


def test_capture_from_html_takes_the_html_and_options_but_no_method() -> None:
    import screenshotscout

    for client_class in (
        screenshotscout.ScreenshotScoutClient,
        screenshotscout.AsyncScreenshotScoutClient,
    ):
        parameters = signature(client_class.capture_from_html).parameters
        assert tuple(parameters) == ("self", "html", "options")
        assert parameters["options"].default is None
