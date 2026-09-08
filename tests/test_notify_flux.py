import hashlib
import hmac
import importlib.util
import pathlib
import urllib.error
from unittest.mock import MagicMock

import pytest

spec = importlib.util.spec_from_file_location(
    "notify_flux", pathlib.Path(__file__).resolve().parents[1] / "notify-flux/notify.py"
)
notify_flux = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify_flux)


def test_signs_exact_request_body(monkeypatch):
    send = MagicMock()
    monkeypatch.setattr(notify_flux.urllib.request, "urlopen", send)
    assert notify_flux.notify("https://flux.example/hook", "test-token", "abc123") == 0
    request = send.call_args.args[0]
    assert request.data == b'{"sha":"abc123"}'
    assert request.method == "POST"
    expected = hmac.new(b"test-token", request.data, hashlib.sha256).hexdigest()
    assert request.get_header("X-signature") == f"sha256={expected}"
    assert send.call_args.kwargs == {"timeout": 30}


@pytest.mark.parametrize("url,token,sha,result", [
    ("", "", "abc123", 0),
    ("https://flux.example/hook", "", "abc123", 1),
    ("", "test-token", "abc123", 1),
    ("http://flux.example/hook", "test-token", "abc123", 1),
    ("https://flux.example/hook", "test-token", "", 1),
])
def test_invalid_or_absent_configuration_never_sends(monkeypatch, url, token, sha, result):
    send = MagicMock()
    monkeypatch.setattr(notify_flux.urllib.request, "urlopen", send)
    assert notify_flux.notify(url, token, sha) == result
    send.assert_not_called()


def test_failure_does_not_print_credentials(monkeypatch, capsys):
    url = "https://flux.example/private-hook"
    token = "test-private-token"
    send = MagicMock(side_effect=urllib.error.URLError(url + token))
    monkeypatch.setattr(notify_flux.urllib.request, "urlopen", send)
    assert notify_flux.notify(url, token, "abc123") == 1
    output = capsys.readouterr().out
    assert url not in output
    assert token not in output
    assert "::error::" in output
