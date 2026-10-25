from pathlib import Path

path = Path("tests/test_cli.py")
content = path.read_text(encoding="utf-8")

old = '''    assert first_service.runtime is runtime
    assert second_service.runtime is runtime
'''

new = '''    assert first_service._runtime is runtime
    assert second_service._runtime is runtime
'''

if content.count(old) != 1:
    raise SystemExit(
        "Expected assertions were not found exactly once. No changes made."
    )

content = content.replace(old, new, 1)
path.write_text(content, encoding="utf-8")

print("Corrected runtime assertions to use the existing _runtime attribute.")
