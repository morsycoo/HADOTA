from pathlib import Path

path = Path("app/web/main.py")
content = path.read_text(encoding="utf-8")

old = '''            if session_manager is not None:
                session_manager.cleanup_expired()

                # Remove remaining in-memory sessions and close their services.
                with session_manager._lock:
                    session_ids = list(session_manager._sessions)

                for session_id in session_ids:
                    session_manager.delete_session(session_id)
'''

new = '''            if session_manager is not None:
                # Close all remaining in-memory sessions and their services.
                session_manager.close_all()
'''

if content.count(old) != 1:
    raise SystemExit(
        "Expected shutdown block was not found exactly once. No changes made."
    )

content = content.replace(old, new, 1)
path.write_text(content, encoding="utf-8")

print("Updated main.py to use SessionManager.close_all().")
