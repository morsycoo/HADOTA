from pathlib import Path

path = Path("tests/test_web_sessions.py")
content = path.read_text(encoding="utf-8")
lines = content.splitlines()

print("Last 6 lines before repair:")
for number, line in enumerate(lines[-6:], start=max(1, len(lines) - 5)):
    print(f"{number}: {line!r}")

if not lines or lines[-1].strip() != r"\n":
    raise SystemExit(
        "Expected literal backslash-n on the final line was not found. "
        "No changes made."
    )

# Remove only the erroneous final line.
lines.pop()
path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("\nRemoved the erroneous final line only.")
