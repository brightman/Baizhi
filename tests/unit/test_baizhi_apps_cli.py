from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest


CLI_SOURCE = Path(__file__).resolve().parents[2] / "tools" / "baizhi-apps-cli" / "src"
sys.path.insert(0, str(CLI_SOURCE))

from baizhi_apps_cli.archive import package_static_directory  # noqa: E402
from baizhi_apps_cli.client import ApiClient, ApiError  # noqa: E402
from baizhi_apps_cli.config import HostConfig, HostConfigError, normalize_host  # noqa: E402
from baizhi_apps_cli.credentials import CredentialError, CredentialStore  # noqa: E402
from baizhi_apps_cli.policy import ConfirmationRequired, require_confirmation  # noqa: E402


class MemoryKeyring:
    priority = 1
    __module__ = "keyring.backends.macOS"

    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[(service, username)] = password

    def delete_password(self, service, username):
        self.values.pop((service, username), None)


def test_host_config_prefers_environment_and_validates_origins(tmp_path):
    config_path = tmp_path / "hosts.json"
    config = HostConfig(
        environ={"BAIZHI_APPS_HOST_TEST": "https://env.example.test"},
        config_path=config_path,
    )
    config.set("test", "https://file.example.test")

    assert config.resolve("test") == "https://env.example.test"
    assert HostConfig(environ={}, config_path=config_path).resolve("test") == "https://file.example.test"
    assert normalize_host("http://127.0.0.1:8787/") == "http://127.0.0.1:8787"
    with pytest.raises(HostConfigError, match="HTTPS"):
        config.set("production", "http://apps.example.test")
    with pytest.raises(HostConfigError):
        normalize_host("https://user:secret@example.test/path?token=x")


def test_credential_store_uses_host_keyed_os_store_and_expiry(tmp_path):
    backend = MemoryKeyring()
    store = CredentialStore(backend=backend, now=lambda: 100)
    store.save("https://apps.example.test", {"token": "secret-token", "expires_at": 200})

    assert store.load("https://apps.example.test")["token"] == "secret-token"
    assert "secret-token" not in repr(backend.values.keys())
    with pytest.raises(CredentialError, match="expired"):
        CredentialStore(backend=backend, now=lambda: 201).load("https://apps.example.test")


def test_credential_store_fails_closed_when_backend_is_unavailable():
    class DisabledKeyring(MemoryKeyring):
        priority = 0

    with pytest.raises(CredentialError, match="secure credential store"):
        CredentialStore(backend=DisabledKeyring())

    class PlaintextKeyring:
        priority = 1

    with pytest.raises(CredentialError, match="plaintext fallback is disabled"):
        CredentialStore(backend=PlaintextKeyring())


def test_api_client_sends_only_bearer_and_does_not_follow_redirects():
    observed = []

    def handler(request):
        observed.append(request)
        return httpx.Response(302, headers={"Location": "https://other.example.test/steal"})

    api = ApiClient("https://apps.example.test", "secret-token", transport=httpx.MockTransport(handler))
    assert api.client._trust_env is False
    with pytest.raises(ApiError) as error:
        api.request("GET", "/v1/apps")

    assert error.value.http_status == 302
    assert len(observed) == 1
    assert observed[0].headers["authorization"] == "Bearer secret-token"
    assert "secret-token" not in str(error.value)


def test_api_client_preserves_machine_error_code_without_echoing_request_token():
    api = ApiClient(
        "https://apps.example.test",
        "secret-token",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(403, json={"detail": {"code": "APP_ACCESS_DENIED", "message": "forbidden"}})
        ),
    )

    with pytest.raises(ApiError) as error:
        api.request("GET", "/v1/apps/private")

    assert error.value.code == "APP_ACCESS_DENIED"
    assert error.value.http_status == 403
    assert "secret-token" not in str(error.value)


def test_confirmation_policy_requires_flags_for_production_writes_and_destructive_actions():
    with pytest.raises(ConfirmationRequired):
        require_confirmation("production", "data.create", "crm/leads", confirmed=False)
    with pytest.raises(ConfirmationRequired):
        require_confirmation("test", "data.delete", "crm/leads/rec-1", confirmed=False)
    with pytest.raises(ConfirmationRequired):
        require_confirmation("staging", "h5.publish", "crm/release-2", confirmed=False)

    require_confirmation("test", "data.create", "crm/leads", confirmed=False)
    require_confirmation("production", "apps.create", "crm", confirmed=True)


def test_static_package_requires_index_rejects_symlinks_and_writes_zip_root(tmp_path):
    source = tmp_path / "site"
    source.mkdir()
    (source / "index.html").write_text("<h1>CRM</h1>", encoding="utf-8")
    (source / "assets").mkdir()
    (source / "assets" / "app.js").write_text("window.app = true", encoding="utf-8")
    output = tmp_path / "site.zip"

    result = package_static_directory(source, output)

    assert result["file_count"] == 2
    assert output.is_file()
    import zipfile
    with zipfile.ZipFile(output) as archive:
        assert "index.html" in archive.namelist()
        assert "assets/app.js" in archive.namelist()

    no_index = tmp_path / "no-index"
    no_index.mkdir()
    (no_index / "readme.txt").write_text("not a website", encoding="utf-8")
    with pytest.raises(ValueError, match="H5_INDEX_REQUIRED"):
        package_static_directory(no_index, tmp_path / "bad.zip")

    linked = tmp_path / "linked"
    linked.mkdir()
    (linked / "index.html").write_text("ok", encoding="utf-8")
    (linked / "outside.txt").write_text("outside", encoding="utf-8")
    (linked / "escape.txt").symlink_to(tmp_path / "outside.txt")
    with pytest.raises(ValueError, match="H5_SYMLINK_NOT_ALLOWED"):
        package_static_directory(linked, tmp_path / "linked.zip")

    with pytest.raises(ValueError, match="H5_OUTPUT_EXISTS"):
        package_static_directory(source, output)
