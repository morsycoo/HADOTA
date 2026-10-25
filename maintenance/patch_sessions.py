from pathlib import Path

path = Path("app/web/sessions.py")
content = path.read_text(encoding="utf-8")

old = """    conversation_id: str
    service: Any


@dataclass
class AnonymousSession:"""

new = """    conversation_id: str
    service: Any
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class AnonymousSession:"""

if old not in content:
    raise SystemExit(
        "Expected class fields were not found. No changes were made."
    )

path.write_text(content.replace(old, new, 1), encoding="utf-8")

print("Added an independent lock to ConversationEntry.")
