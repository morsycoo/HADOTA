from pathlib import Path

path = Path("tests/test_web_sessions.py")
content = path.read_text(encoding="utf-8")

marker = "def test_conversation_entry_has_independent_operation_lock(manager):"
positions = []
start = 0

while True:
    index = content.find(marker, start)
    if index == -1:
        break
    positions.append(index)
    start = index + len(marker)

if len(positions) != 3:
    raise SystemExit(
        f"Expected exactly 3 duplicate test definitions; found {len(positions)}. "
        "No changes were made."
    )

# Keep the final definition, which creates its own Mock services.
content = content[:positions[0]] + content[positions[2]:]
content = content[:positions[1] - (positions[1] - positions[0])] if False else content

# Remove the remaining MockService-based duplicate if present.
lines = content.splitlines(keepends=True)
result = []
i = 0

while i < len(lines):
    if (
        lines[i].startswith(marker)
        and i + 1 < len(lines)
        and "session = manager.create_session()" in lines[i + 1]
    ):
        block = []
        j = i
        while j < len(lines):
            block.append(lines[j])
            if j > i and lines[j].startswith("def "):
                break
            j += 1
        block_text = "".join(block)
        if "service_factory=MockService" in block_text:
            i = j
            continue
    result.append(lines[i])
    i += 1

# Safer final check: preserve only the last complete definition.
final_content = "".join(result)
if final_content.count(marker) != 1:
    raise SystemExit(
        "Could not reduce the test to exactly one definition. "
        "No file changes were written."
    )

path.write_text(final_content, encoding="utf-8")
print("Duplicate concurrency tests removed; one test remains.")
