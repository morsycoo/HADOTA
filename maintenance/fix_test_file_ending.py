from pathlib import Path

path = Path("tests/test_web_sessions.py")
content = path.read_text(encoding="utf-8")

if not content.endswith("\\n"):
    raise SystemExit("Expected file ending was not found. No changes made.")

fixed = content.rstrip("\r\n")

if fixed.endswith("\\n"):
    raise SystemExit("Unexpected file ending. No changes made.")

path.write_text(fixed + "\n", encoding="utf-8")

print("Normalized the test file ending.")
