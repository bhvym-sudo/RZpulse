import pytest

from rzpulse.config import Settings


@pytest.fixture
def settings():
    return Settings(mode="test", key_id="rzp_test_unit", key_secret="unit-secret")


@pytest.fixture(autouse=True)
def clean_credentials(monkeypatch):
    import os
    for name in os.environ:
        if name.startswith("RZP_"):
            monkeypatch.delenv(name)
