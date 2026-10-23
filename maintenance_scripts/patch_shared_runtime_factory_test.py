from pathlib import Path

path = Path("tests/test_cli.py")
content = path.read_text(encoding="utf-8")

test_name = "test_shared_runtime_factory_creates_independent_services"

if test_name in content:
    raise SystemExit("The test already exists. No changes made.")

test_code = '''

def test_shared_runtime_factory_creates_independent_services():
    from unittest.mock import Mock

    from app.cli import create_conversation_service_with_runtime

    runtime = Mock()
    runtime.settings = Mock()

    first_service = create_conversation_service_with_runtime(runtime)
    second_service = create_conversation_service_with_runtime(runtime)

    assert first_service is not second_service
    assert first_service.conversation is not second_service.conversation
    assert first_service.runtime is runtime
    assert second_service.runtime is runtime

    runtime.close.assert_not_called()
'''

content = content.rstrip() + test_code + "\n"
path.write_text(content, encoding="utf-8")

print("Added shared-runtime factory test.")
