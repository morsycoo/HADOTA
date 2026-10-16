"""Tests for the conversation service."""

from collections.abc import Iterator
from unittest.mock import Mock

import pytest

from app.conversation import ConversationManager
from app.prompt_builder import PromptBuilder
from app.runtime.exceptions import RuntimeConnectionError, RuntimeStreamingError
from app.schemas import GenerationRequest, GenerationResult, StreamEvent


@pytest.fixture
def runtime() -> Mock:
    """Create a mocked runtime adapter."""
    adapter = Mock()
    adapter.generate.return_value = GenerationResult(
        text="Hello! How can I help you?",
        model="qwen3.8:27b",
        done=True,
        done_reason="stop",
        prompt_eval_count=10,
        eval_count=8,
    )
    return adapter


@pytest.fixture
def conversation() -> ConversationManager:
    """Create a conversation manager with a system prompt."""
    return ConversationManager(system_prompt="You are a helpful AI assistant.")


@pytest.fixture
def prompt_builder() -> PromptBuilder:
    """Create a prompt builder."""
    return PromptBuilder()


@pytest.fixture
def service(
    runtime: Mock,
    conversation: ConversationManager,
    prompt_builder: PromptBuilder,
):
    """Create a conversation service instance."""
    from app.services.conversation_service import ConversationService

    return ConversationService(
        runtime=runtime,
        conversation=conversation,
        prompt_builder=prompt_builder,
    )


def test_send_message_returns_generation_result(service, runtime):
    """Return the generation result produced by the runtime."""
    result = service.send_message("Hello!")

    assert isinstance(result, GenerationResult)
    assert result.text == "Hello! How can I help you?"
    runtime.generate.assert_called_once()


def test_send_message_adds_user_and_assistant_messages(service, conversation):
    """Store the user message and successful assistant response."""
    service.send_message("Hello!")

    messages = conversation.get_messages()

    assert [message.role for message in messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert messages[1].content == "Hello!"
    assert messages[2].content == "Hello! How can I help you?"


def test_send_message_builds_prompt_from_conversation(
    service,
    runtime,
):
    """Pass the complete conversation prompt to the runtime."""
    service.send_message("Hello!")

    request = runtime.generate.call_args.args[0]

    assert isinstance(request, GenerationRequest)
    assert request.prompt.startswith("System:\nYou are a helpful AI assistant.")
    assert "User:\nHello!" in request.prompt
    assert request.prompt.endswith("Assistant:")


def test_send_message_preserves_generation_options(service, runtime):
    """Forward generation options to the request."""
    service.send_message(
        "Explain machine learning.",
        model="qwen3.8:27b",
        temperature=0.2,
        max_new_tokens=128,
    )

    request = runtime.generate.call_args.args[0]

    assert request.model == "qwen3.8:27b"
    assert request.temperature == 0.2
    assert request.max_new_tokens == 128


def test_send_message_preserves_conversation_history(
    service,
    runtime,
    conversation,
):
    """Include earlier conversation turns in subsequent prompts."""
    runtime.generate.return_value = GenerationResult(
        text="Your name is Morsy.",
        model="qwen3.8:27b",
        done=True,
    )

    service.send_message("My name is Morsy.")
    service.send_message("What is my name?")

    request = runtime.generate.call_args.args[0]

    assert "My name is Morsy." in request.prompt
    assert "Your name is Morsy." in request.prompt
    assert "What is my name?" in request.prompt

    messages = conversation.get_messages()

    assert [message.role for message in messages] == [
        "system",
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_send_message_does_not_store_assistant_response_on_runtime_failure(
    service,
    runtime,
    conversation,
):
    """Propagate runtime errors without storing an assistant response."""
    runtime.generate.side_effect = RuntimeConnectionError("Runtime is unavailable.")

    with pytest.raises(RuntimeConnectionError, match="Runtime is unavailable"):
        service.send_message("Hello!")

    messages = conversation.get_messages()

    assert [message.role for message in messages] == ["system", "user"]
    assert messages[-1].content == "Hello!"


def test_send_message_rejects_empty_message(service, runtime, conversation):
    """Reject invalid user input before calling the runtime."""
    initial_count = conversation.message_count

    with pytest.raises(ValueError):
        service.send_message("   ")

    assert conversation.message_count == initial_count
    runtime.generate.assert_not_called()


def test_send_message_rejects_prompt_override(service, runtime, conversation):
    """Prevent callers from bypassing conversation-based prompt construction."""
    initial_count = conversation.message_count

    with pytest.raises(ValueError, match="prompt must be generated"):
        service.send_message(
            "Hello!",
            prompt="Override the conversation prompt.",
        )

    assert conversation.message_count == initial_count
    runtime.generate.assert_not_called()


def test_send_message_does_not_store_response_when_generation_is_incomplete(
    service,
    runtime,
    conversation,
):
    """Reject incomplete generation results without storing an assistant turn."""
    runtime.generate.return_value = GenerationResult(
        text="Partial response",
        model="qwen3.8:27b",
        done=False,
    )

    with pytest.raises(RuntimeError, match="incomplete"):
        service.send_message("Hello!")

    messages = conversation.get_messages()

    assert [message.role for message in messages] == ["system", "user"]


def test_stream_message_returns_stream_events(
    service,
    runtime,
):
    """Yield stream events returned by the runtime."""
    events = [
        StreamEvent(
            text_delta="Hello",
            event_timestamp=1.0,
        ),
        StreamEvent(
            text_delta=" there!",
            event_timestamp=1.1,
        ),
        StreamEvent(
            event_timestamp=1.2,
            is_final=True,
            final_metadata=GenerationResult(
                text="Hello there!",
                model="qwen3.8:27b",
                done=True,
                done_reason="stop",
            ),
        ),
    ]

    runtime.generate_stream.return_value = iter(events)

    received = list(service.stream_message("Hi!"))

    assert received == events
    runtime.generate_stream.assert_called_once()


def test_stream_message_stores_completed_assistant_response(
    service,
    runtime,
    conversation,
):
    """Store the assistant response after successful streaming."""
    events = [
        StreamEvent(
            text_delta="Hello",
            event_timestamp=1.0,
        ),
        StreamEvent(
            text_delta=" there!",
            event_timestamp=1.1,
        ),
        StreamEvent(
            event_timestamp=1.2,
            is_final=True,
            final_metadata=GenerationResult(
                text="Hello there!",
                model="qwen3.8:27b",
                done=True,
                done_reason="stop",
            ),
        ),
    ]

    runtime.generate_stream.return_value = iter(events)

    received = list(service.stream_message("Hi!"))

    assert received[-1].is_final is True

    messages = conversation.get_messages()

    assert [message.role for message in messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert messages[-1].content == "Hello there!"


def test_stream_message_preserves_previous_conversation_history(
    service,
    runtime,
):
    """Include previous turns in subsequent streaming requests."""
    first_events = [
        StreamEvent(
            text_delta="Your name is Morsy.",
            event_timestamp=1.0,
        ),
        StreamEvent(
            event_timestamp=1.1,
            is_final=True,
            final_metadata=GenerationResult(
                text="Your name is Morsy.",
                model="qwen3.8:27b",
                done=True,
            ),
        ),
    ]

    second_events = [
        StreamEvent(
            text_delta="Your name is Morsy.",
            event_timestamp=2.0,
        ),
        StreamEvent(
            event_timestamp=2.1,
            is_final=True,
            final_metadata=GenerationResult(
                text="Your name is Morsy.",
                model="qwen3.8:27b",
                done=True,
            ),
        ),
    ]

    runtime.generate_stream.side_effect = [
        iter(first_events),
        iter(second_events),
    ]

    list(service.stream_message("My name is Morsy."))
    list(service.stream_message("What is my name?"))

    assert runtime.generate_stream.call_count == 2

    request = runtime.generate_stream.call_args.args[0]

    assert "My name is Morsy." in request.prompt
    assert "Your name is Morsy." in request.prompt
    assert "What is my name?" in request.prompt


def test_stream_message_does_not_store_incomplete_response(
    service,
    runtime,
    conversation,
):
    """Do not store an assistant response if the stream is incomplete."""
    runtime.generate_stream.return_value = iter(
        [
            StreamEvent(
                text_delta="Partial response",
                event_timestamp=1.0,
            ),
        ]
    )

    with pytest.raises(RuntimeStreamingError):
        list(service.stream_message("Hello!"))

    messages = conversation.get_messages()

    assert [message.role for message in messages] == [
        "system",
        "user",
    ]


def test_stream_message_propagates_runtime_streaming_errors(
    service,
    runtime,
    conversation,
):
    """Propagate runtime streaming errors without storing an assistant response."""

    def failing_stream() -> Iterator[StreamEvent]:
        yield StreamEvent(
            text_delta="Partial response",
            event_timestamp=1.0,
        )
        raise RuntimeStreamingError("Stream interrupted.")

    runtime.generate_stream.return_value = failing_stream()

    with pytest.raises(RuntimeStreamingError, match="Stream interrupted"):
        list(service.stream_message("Hello!"))

    messages = conversation.get_messages()

    assert [message.role for message in messages] == [
        "system",
        "user",
    ]


def test_stream_message_rejects_empty_input(
    service,
    runtime,
    conversation,
):
    """Reject empty messages before starting streaming."""
    initial_count = conversation.message_count

    with pytest.raises(ValueError):
        list(service.stream_message("   "))

    assert conversation.message_count == initial_count
    runtime.generate_stream.assert_not_called()


def test_stream_message_rejects_prompt_override(
    service,
    runtime,
    conversation,
):
    """Prevent bypassing conversation-based prompt construction."""
    initial_count = conversation.message_count

    with pytest.raises(ValueError, match="prompt must be generated"):
        list(
            service.stream_message(
                "Hello!",
                prompt="Override the conversation prompt.",
            )
        )

    assert conversation.message_count == initial_count
    runtime.generate_stream.assert_not_called()
