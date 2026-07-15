from inspect import signature


def test_package_is_importable() -> None:
    import screenshotscout

    assert screenshotscout.__name__ == "screenshotscout"


def test_client_configuration_surface_is_fixed() -> None:
    import screenshotscout

    assert tuple(signature(screenshotscout.ScreenshotScoutClient).parameters) == (
        "access_key",
        "secret_key",
        "http_client",
    )
    assert tuple(signature(screenshotscout.AsyncScreenshotScoutClient).parameters) == (
        "access_key",
        "secret_key",
        "http_client",
    )
    assert "RequestTimeout" not in screenshotscout.__all__
    assert not hasattr(screenshotscout, "RequestTimeout")
