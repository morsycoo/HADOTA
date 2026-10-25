from pathlib import Path

path = Path("tests/test_web_sessions.py")
content = path.read_text(encoding="utf-8")

start_marker = "def test_close_all_closes_all_sessions_and_conversations():"
end_marker = "def test_close_all_is_idempotent():"

if content.count(start_marker) != 1 or content.count(end_marker) != 1:
    raise SystemExit("Expected test definitions were not found exactly once. No changes made.")

start = content.index(start_marker)
end = content.index(end_marker)

replacement = '''def test_close_all_closes_all_sessions_and_conversations():
    from unittest.mock import Mock

    manager = SessionManager()
    first_service = Mock()
    second_service = Mock()

    first_session = manager.create_session()
    second_session = manager.create_session()

    manager.create_conversation(
        first_session.session_id,
        service_factory=lambda: first_service,
    )
    manager.create_conversation(
        second_session.session_id,
        service_factory=lambda: second_service,
    )

    closed_sessions = manager.close_all()

    assert closed_sessions == 2
    assert manager.active_session_count == 0
    first_service.close.assert_called_once_with()
    second_service.close.assert_called_once_with()

    with pytest.raises(SessionNotFoundError):
        manager.get_session(first_session.session_id)

    with pytest.raises(SessionNotFoundError):
        manager.get_session(second_session.session_id)


'''

content = content[:start] + replacement + content[end:]

start_marker = "def test_close_all_is_idempotent():"
start = content.index(start_marker)

# Replace the remainder of this final test, which is at the end of the file.
replacement = '''def test_close_all_is_idempotent():
    from unittest.mock import Mock

    manager = SessionManager()
    service = Mock()
    session = manager.create_session()

    manager.create_conversation(
        session.session_id,
        service_factory=lambda: service,
    )

    assert manager.close_all() == 1
    assert manager.close_all() == 0

    assert manager.active_session_count == 0
    service.close.assert_called_once_with()
'''

content = content[:start] + replacement + "\\n"
path.write_text(content, encoding="utf-8")

print("Updated both close_all() tests to use the existing Mock pattern.")
