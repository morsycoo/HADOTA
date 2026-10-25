from pathlib import Path

path = Path("app/web/sessions.py")
content = path.read_text(encoding="utf-8")

old_entry = """    service: Any
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class AnonymousSession:"""

new_entry = """    service: Any
    lock: threading.Lock = field(default_factory=threading.Lock)
    closing: bool = False


@dataclass
class AnonymousSession:"""

old_get = """        with session.lock:
            entry = session.conversations.get(conversation_id)

            if entry is None:
                raise SessionNotFoundError("The conversation was not found.")

            return entry
"""

new_get = """        with session.lock:
            entry = session.conversations.get(conversation_id)

            if entry is None:
                raise SessionNotFoundError("The conversation was not found.")

            with entry.lock:
                if entry.closing:
                    raise SessionNotFoundError("The conversation was not found.")

            return entry
"""

old_delete = """        with session.lock:
            entry = session.conversations.pop(conversation_id, None)

        if entry is None:
            return False

        self._close_service(entry.service)
        return True
"""

new_delete = """        with session.lock:
            entry = session.conversations.get(conversation_id)

            if entry is None:
                return False

            with entry.lock:
                entry.closing = True
                session.conversations.pop(conversation_id, None)

        with entry.lock:
            self._close_service(entry.service)

        return True
"""

old_close_sessions = """            with session.lock:
                entries = list(session.conversations.values())
                session.conversations.clear()

            for entry in entries:
                self._close_service(entry.service)
"""

new_close_sessions = """            with session.lock:
                entries = list(session.conversations.values())

                for entry in entries:
                    with entry.lock:
                        entry.closing = True

                session.conversations.clear()

            for entry in entries:
                with entry.lock:
                    self._close_service(entry.service)
"""

replacements = [
    (old_entry, new_entry, "ConversationEntry lifecycle state"),
    (old_get, new_get, "Conversation lookup"),
    (old_delete, new_delete, "Conversation deletion"),
    (old_close_sessions, new_close_sessions, "Session cleanup"),
]

for old, new, label in replacements:
    count = content.count(old)
    if count != 1:
        raise SystemExit(
            f"{label}: expected exactly one matching block, found {count}. "
            "No changes were written."
        )
    content = content.replace(old, new, 1)

path.write_text(content, encoding="utf-8")
print("Updated conversation lifecycle handling.")
