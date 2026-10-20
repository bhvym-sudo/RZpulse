import pytest
from rzpulse.config import ConfigurationError, Settings


def test_missing_credentials(tmp_path):
    with pytest.raises(ConfigurationError, match="Configure"):
        Settings.load(tmp_path / "missing")


@pytest.mark.parametrize("mode,key", [("live", "rzp_test_key"), ("test", "rzp_live_key"),
                                      ("wrong", "rzp_test_key"), ("test", " rzp_test_key")])
def test_bad_mode_or_key(tmp_path, mode, key):
    path = tmp_path / ".env"
    path.write_text(f"RZP_MODE={mode}\nRZP_KEY_ID={key!r}\nRZP_KEY_SECRET=hidden\n")
    with pytest.raises(ConfigurationError) as error:
        Settings.load(path)
    assert "hidden" not in str(error.value)


def test_separate_environments_and_precedence(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("RZP_MODE=test\nRZP_TEST_KEY_ID=rzp_test_file\nRZP_TEST_KEY_SECRET=file-secret\n"
                    "RZP_LIVE_KEY_ID=rzp_live_file\nRZP_LIVE_KEY_SECRET=live-secret\n")
    monkeypatch.setenv("RZP_TEST_KEY_SECRET", "env-secret")
    settings = Settings.load(path)
    assert settings.mode == "test"
    assert settings.key_secret.get_secret_value() == "env-secret"
    assert "env-secret" not in repr(settings)
    monkeypatch.setenv("RZP_MODE", "live")
    assert Settings.load(path).key_id.get_secret_value() == "rzp_live_file"


def test_no_fallback_to_other_mode(tmp_path):
    path = tmp_path / ".env"
    path.write_text("RZP_MODE=live\nRZP_TEST_KEY_ID=rzp_test_unit\nRZP_TEST_KEY_SECRET=hidden\n")
    with pytest.raises(ConfigurationError):
        Settings.load(path)


def test_mode_mismatch_explains_fix_without_revealing_key(tmp_path):
    path = tmp_path / ".env"
    path.write_text("RZP_MODE=test\nRZP_TEST_KEY_ID=rzp_live_private\n"
                    "RZP_TEST_KEY_SECRET=private-secret\n")
    with pytest.raises(ConfigurationError) as error:
        Settings.load(path)
    message = str(error.value)
    assert "key is for LIVE" in message
    assert "RZP_MODE=test" in message
    assert "RZP_LIVE_KEY_ID" in message
    assert "rzp_live_private" not in message
    assert "private-secret" not in message
