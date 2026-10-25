from pathlib import Path

path = Path("tests/test_web_api.py")
content = path.read_text(encoding="utf-8")

test_name = "def test_session_manager_closes_all_sessions_when_application_stops():"

if test_name in content:
    raise SystemExit("Lifecycle cleanup test already exists. No changes made.")

test = '''

def test_session_manager_closes_all_sessions_when_application_stops(monkeypatch):
    from app.web import main

    runtime = make_runtime()
    service = Mock()
    session_manager = Mock()
    session_manager.close_all.return_value = 0

    monkeypatch.setattr(
        main,
        "SessionManager",
        lambda: session_manager,
    )

    app = create_app(make_service_factory(runtime, service))

    with TestClient(app):
        assert app.state.session_manager is session_manager

    session_manager.close_all.assert_called_once_with()
    runtime.close.assert_called_once_with()
'''

content = content.rstrip() + test + "\n"
path.write_text(content, encoding="utf-8")

print("Added application shutdown session-cleanup test.")
