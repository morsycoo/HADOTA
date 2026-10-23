from unittest.mock import Mock
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.config import RuntimeSettings
from app.web.main import create_app


def make_runtime(healthy=True):
    runtime = Mock()
    runtime.health.return_value = healthy
    runtime.close.return_value = None
    return runtime


def make_service_factory(runtime, service):
    def factory():
        return runtime, service
    return factory


def make_service():
    service = Mock()
    service.conversation.get_messages.return_value = []
    return service


def make_app():
    runtime = make_runtime()
    service = make_service()
    return create_app(make_service_factory(runtime, service)), service


def test_create_session_sets_http_only_cookie():
    app, _ = make_app()
    with TestClient(app) as client:
        response = client.post("/api/session")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "hadota_session=" in cookie


def test_create_conversation_requires_session():
    app, _ = make_app()
    with TestClient(app) as client:
        response = client.post("/api/conversations", json={})
    assert response.status_code == 401


def test_create_conversation_returns_conversation_id():
    app, _ = make_app()
    with TestClient(app) as client:
        assert client.post("/api/session").status_code == 200
        response = client.post(
            "/api/conversations",
            json={"title": "Test conversation"},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["conversation_id"]
    assert body["title"] == "Test conversation"


def test_conversation_cannot_be_accessed_from_another_session():
    app, _ = make_app()
    with TestClient(app) as first:
        assert first.post("/api/session").status_code == 200
        created = first.post("/api/conversations", json={})
        assert created.status_code == 201
        conversation_id = created.json()["conversation_id"]
        with TestClient(app) as second:
            assert second.post("/api/session").status_code == 200
            response = second.get(f"/api/conversations/{conversation_id}")
    assert response.status_code == 404


def test_create_conversation_rejects_unknown_request_fields():
    app, _ = make_app()
    with TestClient(app) as client:
        assert client.post("/api/session").status_code == 200
        response = client.post(
            "/api/conversations",
            json={"unexpected": "value"},
        )
    assert response.status_code == 422


def test_send_message_returns_completed_assistant_response():
    app, service = make_app()
    service.send_message.return_value = SimpleNamespace(
        text="Hello from HADOTA",
        done=True,
    )
    with TestClient(app) as client:
        assert client.post("/api/session").status_code == 200
        created = client.post("/api/conversations", json={})
        conversation_id = created.json()["conversation_id"]
        response = client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "Hello"},
        )
    assert response.status_code == 200
    assert response.json()["content"] == "Hello from HADOTA"
    assert response.json()["role"] == "assistant"
    assert response.json()["done"] is True
    service.send_message.assert_called_once_with("Hello")


def test_send_message_rejects_blank_content():
    app, service = make_app()
    with TestClient(app) as client:
        assert client.post("/api/session").status_code == 200
        created = client.post("/api/conversations", json={})
        response = client.post(
            f"/api/conversations/{created.json()['conversation_id']}/messages",
            json={"content": "   "},
        )
    assert response.status_code == 422
    service.send_message.assert_not_called()


def test_send_message_rejects_content_over_limit():
    app, service = make_app()
    with TestClient(app) as client:
        assert client.post("/api/session").status_code == 200
        created = client.post("/api/conversations", json={})
        response = client.post(
            f"/api/conversations/{created.json()['conversation_id']}/messages",
            json={"content": "a" * 4001},
        )
    assert response.status_code == 422
    service.send_message.assert_not_called()


def test_send_message_hides_internal_runtime_errors():
    from app.runtime.exceptions import RuntimeConnectionError

    app, service = make_app()
    service.send_message.side_effect = RuntimeConnectionError(
        "Internal server address and credentials"
    )
    with TestClient(app) as client:
        assert client.post("/api/session").status_code == 200
        created = client.post("/api/conversations", json={})
        response = client.post(
            f"/api/conversations/{created.json()['conversation_id']}/messages",
            json={"content": "Hello"},
        )
    assert response.status_code == 503
    assert "Internal server address and credentials" not in response.text


def test_session_cookie_has_expected_security_attributes():
    app, _ = make_app()
    with TestClient(app) as client:
        response = client.post("/api/session")
    cookie = response.headers.get("set-cookie", "").lower()
    assert response.status_code == 200
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "max-age=14400" in cookie


def test_delete_session_clears_session_cookie():
    app, _ = make_app()
    with TestClient(app) as client:
        assert client.post("/api/session").status_code == 200
        response = client.delete("/api/session")
    assert response.status_code == 200
    cookie = response.headers.get("set-cookie", "").lower()
    assert "hadota_session=" in cookie
    assert "max-age=0" in cookie


def test_session_cookie_secure_setting_enabled():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(cookie_secure=True)
    with TestClient(app) as client:
        response = client.post("/api/session")
    cookie = response.headers.get("set-cookie", "").lower()
    assert response.status_code == 200
    assert "secure" in [part.strip() for part in cookie.split(";")]


def test_session_cookie_secure_setting_disabled():
    app, _ = make_app()
    with TestClient(app) as client:
        response = client.post("/api/session")
    cookie = response.headers.get("set-cookie", "").lower()
    assert "secure" not in [part.strip() for part in cookie.split(";")]


def test_delete_session_cookie_uses_secure_setting():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(cookie_secure=True)
    with TestClient(app) as client:
        assert client.post("/api/session").status_code == 200
        response = client.delete("/api/session")
    cookie = response.headers.get("set-cookie", "").lower()
    attributes = [part.strip() for part in cookie.split(";")]
    assert response.status_code == 200
    assert "secure" in attributes
    assert "max-age=0" in attributes


def test_disallowed_origin_is_rejected():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(
        allowed_origins="http://localhost:8000"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"Origin": "https://evil.example"},
        )
    assert response.status_code == 403
    assert response.json() == {"error": "Origin not allowed."}


def test_allowed_origin_can_create_session():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(
        allowed_origins="http://localhost:8000"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"Origin": "http://localhost:8000"},
        )
    assert response.status_code == 200


def test_request_without_origin_remains_supported():
    app, _ = make_app()
    with TestClient(app) as client:
        response = client.post("/api/session")
    assert response.status_code == 200
from urllib.parse import urlsplit




def test_public_mode_requires_origin_header():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(
        public_mode=True,
        cookie_secure=True,
        allowed_origins="https://example.com",
    )

    with TestClient(app) as client:
        response = client.post("/api/session")

    assert response.status_code == 403
    assert response.json() == {"error": "Origin header required."}

def test_origin_hostname_comparison_is_case_insensitive():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(
        allowed_origins="http://localhost:8000"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"Origin": "http://LOCALHOST:8000"},
        )
    assert response.status_code == 200


def test_origin_different_port_is_rejected():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(
        allowed_origins="http://localhost:8000"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"Origin": "http://localhost:9000"},
        )
    assert response.status_code == 403


def test_origin_with_path_is_rejected():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(
        allowed_origins="http://localhost:8000"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"Origin": "http://localhost:8000/untrusted"},
        )
    assert response.status_code == 403


def test_null_origin_is_rejected():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(
        allowed_origins="http://localhost:8000"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"Origin": "null"},
        )
    assert response.status_code == 403


def test_origin_with_userinfo_is_rejected():
    app, _ = make_app()
    app.state.settings = RuntimeSettings(
        allowed_origins="http://localhost:8000"
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/session",
            headers={"Origin": "http://user@localhost:8000"},
        )
    assert response.status_code == 403


def test_public_mode_rejects_unsafe_settings_before_runtime_creation(
    monkeypatch,
) -> None:
    """Reject unsafe public settings before creating the Ollama runtime."""

    import pytest
    import app.web.main as web_main

    unsafe_settings = RuntimeSettings(
        public_mode=True,
        cookie_secure=False,
        allowed_origins="https://example.com",
    )

    monkeypatch.setattr(
        web_main,
        "load_settings",
        lambda: unsafe_settings,
    )

    runtime_factory = Mock(side_effect=AssertionError("Runtime must not be created."))
    monkeypatch.setattr(web_main, "OllamaRuntime", runtime_factory)

    app = create_app()

    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        with TestClient(app):
            pass

    runtime_factory.assert_not_called()


def test_public_mode_starts_with_secure_settings(monkeypatch) -> None:
    """Allow startup when public-mode security settings are valid."""

    import app.web.main as web_main

    runtime = make_runtime()
    service = make_service()

    secure_settings = RuntimeSettings(
        public_mode=True,
        cookie_secure=True,
        allowed_origins="https://example.com",
    )

    monkeypatch.setattr(web_main, "load_settings", lambda: secure_settings)
    monkeypatch.setattr(
        web_main,
        "OllamaRuntime",
        lambda settings: runtime,
    )

    monkeypatch.setattr(
        web_main,
        "create_conversation_service_with_runtime",
        lambda active_runtime: service,
    )

    app = create_app()

    with TestClient(app):
        assert app.state.settings.public_mode is True
        assert app.state.runtime is runtime

    runtime.close.assert_called_once()

def test_periodic_cleanup_runs_and_shutdown_waits_for_active_cleanup(monkeypatch):
    import threading

    from app.web import main as web_main

    cleanup_started = threading.Event()
    allow_cleanup_to_finish = threading.Event()
    cleanup_finished = threading.Event()
    closed_after_cleanup = []

    class TrackingSessionManager:
        def cleanup_expired(self):
            cleanup_started.set()
            if not allow_cleanup_to_finish.wait(timeout=5):
                raise TimeoutError("Test did not release the cleanup worker.")
            cleanup_finished.set()

        def close_all(self):
            closed_after_cleanup.append(cleanup_finished.is_set())

    monkeypatch.setattr(
        web_main, "SessionManager", TrackingSessionManager
    )
    monkeypatch.setattr(
        web_main, "SESSION_CLEANUP_INTERVAL_SECONDS", 0.01
    )

    app, _ = make_app()
    release_thread = None

    with TestClient(app):
        assert cleanup_started.wait(timeout=2), (
            "Periodic cleanup did not start."
        )
        release_thread = threading.Timer(
            0.1, allow_cleanup_to_finish.set
        )
        release_thread.start()

    if release_thread is not None:
        release_thread.join(timeout=2)
        assert not release_thread.is_alive()

    assert cleanup_finished.is_set()
    assert closed_after_cleanup == [True]


def test_periodic_cleanup_does_not_run_after_shutdown(monkeypatch):
    import time

    from app.web import main as web_main

    session_manager = Mock()

    monkeypatch.setattr(
        web_main, "SessionManager", lambda: session_manager
    )
    monkeypatch.setattr(
        web_main, "SESSION_CLEANUP_INTERVAL_SECONDS", 0.05
    )

    app, _ = make_app()

    with TestClient(app):
        pass

    time.sleep(0.1)

    session_manager.cleanup_expired.assert_not_called()
    session_manager.close_all.assert_called_once_with()
