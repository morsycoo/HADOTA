from pathlib import Path

path = Path("app/web/sessions.py")
content = path.read_text(encoding="utf-8")

if "def conversation_operation(" in content:
    raise SystemExit(
        "conversation_operation already exists. No changes were made."
    )

old_import = """import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable
"""

new_import = """import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator
"""

if content.count(old_import) != 1:
    raise SystemExit("Import block did not match. No changes were made.")

content = content.replace(old_import, new_import, 1)

anchor = """    def delete_conversation(
        self,
        session_id: str,
        conversation_id: str,
    ) -> bool:
"""

method = '''    @contextmanager
    def conversation_operation(
        self,
        session_id: str,
        conversation_id: str,
    ) -> Iterator[ConversationEntry]:
        """Hold a conversation lock for the full duration of an operation."""

        session = self.get_session(session_id)

        with session.lock:
            entry = session.conversations.get(conversation_id)

            if entry is None:
                raise SessionNotFoundError("The conversation was not found.")

            entry.lock.acquire()

            if entry.closing:
                entry.lock.release()
                raise SessionNotFoundError("The conversation was not found.")

        try:
            yield entry
        finally:
            entry.lock.release()

'''

if content.count(anchor) != 1:
    raise SystemExit("Insertion point did not match. No changes were made.")

content = content.replace(anchor, method + anchor, 1)
path.write_text(content, encoding="utf-8")

print("Added conversation_operation().")
