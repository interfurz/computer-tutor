import sys

import pytest
from pydantic import ValidationError

from computer_tutor.storage import Settings, data_directory, load_settings, save_settings


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://remote.example/v1",
        "https://user:pass@example.com",
        "https://example.com?key=secret",
        "file:///etc/passwd",
    ],
)
def test_unsafe_provider_addresses_rejected(endpoint):
    with pytest.raises(ValidationError):
        Settings(endpoint=endpoint)


def test_settings_roundtrip_and_corrupt_file_recovery():
    settings = Settings(endpoint="http://localhost:1234/v1/", model="local-vision")
    save_settings(settings)
    assert load_settings().endpoint == "http://localhost:1234/v1"
    path = data_directory() / "settings.json"
    path.write_text("broken", encoding="utf-8")
    assert load_settings().model == Settings().model
    assert path.read_text() == "broken"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows DPAPI")
def test_windows_api_key_is_encrypted_and_decryptable():
    settings = Settings()
    settings.set_api_key("test-secret-never-a-real-key")
    save_settings(settings)
    assert "test-secret-never-a-real-key" not in (data_directory() / "settings.json").read_text()
    assert load_settings().api_key() == "test-secret-never-a-real-key"
