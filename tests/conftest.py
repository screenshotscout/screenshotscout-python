import pytest


@pytest.fixture(autouse=True)
def _clear_sdk_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep variables set in the developer's own environment out of every test."""

    monkeypatch.delenv("SCREENSHOTSCOUT_ACCESS_KEY", raising=False)
    monkeypatch.delenv("SCREENSHOTSCOUT_SECRET_KEY", raising=False)
    monkeypatch.delenv("SCREENSHOTSCOUT_BASE_URL", raising=False)
