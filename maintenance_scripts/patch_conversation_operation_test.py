from pathlib import Path

path = Path("tests/test_web_sessions.py")
content = path.read_text(encoding="utf-8")

if "test_conversation_operation_holds_lock_until_operation_finishes" in content:
    raise SystemExit("The test already exists. No changes made.")

test_code = '''


def test_conversation_operation_holds_lock_until_operation_finishes(manager):
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
    deletion_started = threading.Event()
    deletion_finished = threading.Event()
    deletion_result = []

    def active_operation():
        with manager.conversation_operation(
            session.session_id,
            entry.conversation_id,
        ) as active_entry:
            assert active_entry is entry
            operation_started.set()
            assert allow_operation_to_finish.wait(timeout=5)

    def delete_operation():
        assert operation_started.wait(timeout=5)
        deletion_started.set()
        deletion_result.append(
            manager.delete_conversation(
                session.session_id,
                entry.conversation_id,
            )
        )
        deletion_finished.set()

    operation_thread = threading.Thread(target=active_operation)
    deletion_thread = threading.Thread(target=delete_operation)

    operation_thread.start()
    deletion_thread.start()

    try:
        assert operation_started.wait(timeout=5)
        assert deletion_started.wait(timeout=5)

        # Give the deletion thread an opportunity to reach the lock.
        assert not deletion_finished.wait(timeout=0.1)
        service.close.assert_not_called()
    finally:
        allow_operation_to_finish.set()
        operation_thread.join(timeout=5)
        deletion_thread.join(timeout=5)

    assert not operation_thread.is_alive()
    assert not deletion_thread.is_alive()
    assert deletion_finished.is_set()
    assert deletion_result == [True]
    service.close.assert_called_once_with()

    with pytest.raises(SessionNotFoundError):
        with manager.conversation_operation(
            session.session_id,
            entry.conversation_id,
        ):
            pass
'''

content = content.rstrip() + test_code + "\\n"
path.write_text(content, encoding="utf-8")

print("Added conversation_operation concurrency test.")
