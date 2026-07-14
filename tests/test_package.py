def test_package_is_importable() -> None:
    import screenshotscout

    assert screenshotscout.__name__ == "screenshotscout"
