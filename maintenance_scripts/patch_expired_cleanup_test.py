from pathlib import Path

path = Path("tests/test_web_sessions.py")
content = path.read_text(encoding="utf-8")

test_name = "test_conversation_operation_blocks_expired_session_cleanup"

if test_name in content:
    raise SystemExit("The test already exists. No changes made.")

test_code = '''

def test_conversation_operation_blocks_expired_session_cleanup(manager, clock):
    import threading
    from unittest.mock import Mock

    session = manager.create_session()
    service = Mock()

    entry = manager.create_conversation(
        session.session_id,
        service_factory=lambda: service,
    )

    operation_started = threading.Event()
    allow_operation_to_finish = threading.Event()
    cleanup_started = threading.Event()
    cleanup_finished = threading.Event()
    cleanup_result = []

    def active_operation():
        with manager.conversation_operation(
            session.session_id,
            entry.conversation_id,
        ) as active_entry:
            assert active_entry is entry
            operation_started.set()
            assert allow_operation_to_finish.wait(timeout=5)

    def cleanup():
        assert operation_started.wait(timeout=5)
        clock.advance(60)
        cleanup_started.set()
        cleanup_result.append(manager.cleanup_expired())
        cleanup_finished.set()

    operation_thread = threading.Thread(target=active_operation)
    cleanup_thread = threading.Thread(target=cleanup)

    operation_thread.start()
    cleanup_thread.start()

    try:
        assert operation_started.wait(timeout=5)
        assert cleanup_started.wait(timeout=5)
        assert not cleanup_finished.wait(timeout=0.1)
        service.close.assert_not_called()
    finally:
        allow_operation_to_finish.set()
        operation_thread.join(timeout=5)
        cleanup_thread.join(timeout=5)

    assert not operation_thread.is_alive()
    assert not cleanup_thread.is_alive()
    assert cleanup_finished.is_set()
    assert cleanup_result == [1]
    service.close.assert_called_once_with()

    with pytest.raises(SessionNotFoundError):
        manager.get_session(session.session_id)
'''

content = content.rstrip() + test_code + "\n"
path.write_text(content, encoding="utf-8")

print("Added expired-session cleanup concurrency test.")
