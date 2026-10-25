from pathlib import Path

path = Path("app/cli.py")
content = path.read_text(encoding="utf-8")

function_name = "def create_conversation_service_with_runtime("

if function_name in content:
    raise SystemExit("The factory already exists. No changes made.")

anchor = '''    return runtime, service


def _print_help() -> None:
'''

new_block = '''    return runtime, service


def create_conversation_service_with_runtime(
    runtime: OllamaRuntime,
) -> ConversationService:
    """Create an independent conversation service using a shared runtime."""

    conversation = ConversationManager()
    prompt_builder = PromptBuilder()

    return ConversationService(
        runtime=runtime,
        conversation=conversation,
        prompt_builder=prompt_builder,
        settings=runtime.settings,
    )


def _print_help() -> None:
'''

if content.count(anchor) != 1:
    raise SystemExit(
        "Expected insertion point was not found exactly once. No changes made."
    )

content = content.replace(anchor, new_block, 1)
path.write_text(content, encoding="utf-8")

print("Added create_conversation_service_with_runtime().")
