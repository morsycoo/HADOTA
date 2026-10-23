from pathlib import Path

path = Path("app/web/sessions.py")
content = path.read_text(encoding="utf-8")

if "    def close_all(self)" in content:
    raise SystemExit("close_all() already exists. No changes made.")

anchor = '''    def cleanup_expired(self) -> int:
        """Remove expired sessions and close their conversation services."""
'''

new_method = '''    def close_all(self) -> int:
        """Remove all sessions and close their conversation services."""

        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()

        self._close_sessions(sessions)
        return len(sessions)

    def cleanup_expired(self) -> int:
        """Remove expired sessions and close their conversation services."""
'''

if content.count(anchor) != 1:
    raise SystemExit(
        "Expected insertion point was not found exactly once. No changes made."
    )

content = content.replace(anchor, new_method, 1)
path.write_text(content, encoding="utf-8")

print("Added SessionManager.close_all().")
