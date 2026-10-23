from pathlib import Path

path = Path("tests/test_web_sessions.py")
content = path.read_text(encoding="utf-8")

if not content.endswith("\\n"):
    raise SystemExit(
        "Expected the file to end with a literal backslash-n sequence. "
        "No changes made."
    )

content = content[:-2] + "\n"
path.write_text(content, encoding="utf-8")

print("Removed the accidental literal \\n at end of test file.")
