from pathlib import Path

path = Path("tests/test_web_sessions.py")
content = path.read_text(encoding="utf-8")

if "def test_close_all_closes_all_sessions_and_conversations" in content:
    raise SystemExit("close_all tests already exist. No changes made.")

tests = '''

def test_close_all_closes_all_sessions_and_conversations():
    manager = SessionManager()
    first_service = FakeService()
    second_service = FakeService()

    first_session = manager.create_session()
    second_session = manager.create_session()

    manager.create_conversation(first_session.session_id, first_service)
    manager.create_conversation(second_session.session_id, second_service)

    closed_sessions = manager.close_all()

    assert closed_sessions == 2
    assert manager.active_session_count == 0
    assert first_service.close_calls == 1
    assert second_service.close_calls == 1

    with pytest.raises(SessionNotFoundError):
        manager.get_session(first_session.session_id)

    with pytest.raises(SessionNotFoundError):
        manager.get_session(second_session.session_id)


def test_close_all_is_idempotent():
    manager = SessionManager()
    service = FakeService()
    session = manager.create_session()
    manager.create_conversation(session.session_id, service)

    assert manager.close_all() == 1
    assert manager.close_all() == 0

    assert manager.active_session_count == 0
    assert service.close_calls == 1
'''

content = content.rstrip() + tests + "\n"
path.write_text(content, encoding="utf-8")

print("Added close_all() tests.")
