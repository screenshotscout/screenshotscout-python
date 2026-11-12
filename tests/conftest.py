import pytest


@pytest.fixture(autouse=True)
def _clear_key_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep keys set in the developer's own environment out of every test."""

    monkeypatch.delenv("SCREENSHOTSCOUT_ACCESS_KEY", raising=False)
    monkeypatch.delenv("SCREENSHOTSCOUT_SECRET_KEY", raising=False)
