"""
Tests for the `openedx_webhooks.utils` module.
"""

from openedx_webhooks.utils import flatten_dict, send


def test_flatten_dict_uses_joined_keys():
    """Nested dictionaries are flattened using underscore-separated keys."""
    assert flatten_dict({"user": {"name": "andres", "active": True}}) == {
        "user_name": "andres",
        "user_active": "True",
    }


def test_send_uses_form_encoded_payload_when_requested(monkeypatch):
    """Form-encoded requests send flattened dictionaries instead of a JSON string."""
    captured = {}

    def fake_post(url, data, headers, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        captured["timeout"] = timeout
        return object()

    monkeypatch.setattr("openedx_webhooks.utils.requests.post", fake_post)

    send(
        "https://example.com/webhook",
        {"user": {"name": "andres"}},
        www_form_urlencoded=True,
    )

    assert captured["url"] == "https://example.com/webhook"
    assert captured["data"] == {"user_name": "andres"}
    assert captured["headers"]["Content-type"] == "application/x-www-form-urlencoded"
    assert captured["timeout"] == 10
