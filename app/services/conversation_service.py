"""Conversation orchestration service for the Local AI Assistant."""

from collections.abc import Iterator
from typing import Any

from app.config import RuntimeSettings, load_settings
from app.context.window_manager import ContextWindowManager
from app.conversation import ConversationManager
from app.prompt_builder import PromptBuilder
from app.runtime.base import RuntimeInterface
from app.runtime.exceptions import RuntimeStreamingError
from app.schemas import (
    GenerationRequest,
    GenerationResult,
    StreamEvent,
)


class ConversationService:
    """Coordinate conversation history, prompt construction, and generation."""

    def __init__(
        self,
        runtime: RuntimeInterface,
        conversation: ConversationManager,
        prompt_builder: PromptBuilder,
        context_window_manager: ContextWindowManager | None = None,
        settings: RuntimeSettings | None = None,
    ) -> None:
        self._runtime = runtime
        self._conversation = conversation
        self._prompt_builder = prompt_builder
        self._context_window_manager = context_window_manager
        self._settings = settings or load_settings()

    @property
    def conversation(self) -> ConversationManager:
        """Expose the managed conversation."""
        return self._conversation

    def _build_request(
        self,
        generation_options: dict[str, Any],
    ) -> GenerationRequest:
        """Build a generation request with consistent context settings."""
        messages = self._conversation.get_messages()

        num_ctx = generation_options.get("num_ctx")
        if num_ctx is None:
            num_ctx = self._settings.num_ctx

        max_new_tokens = generation_options.get("max_new_tokens")
        if max_new_tokens is None:
            max_new_tokens = self._settings.max_new_tokens

        if self._context_window_manager is not None:
            messages = self._context_window_manager.fit_messages(
                messages=messages,
                num_ctx=num_ctx,
                max_new_tokens=max_new_tokens,
            )

        resolved_options = {
            **generation_options,
            "num_ctx": num_ctx,
            "max_new_tokens": max_new_tokens,
        }

        return self._prompt_builder.build_request(
            messages,
            **resolved_options,
        )

    def send_message(
        self,
        content: str,
        **generation_options: Any,
    ) -> GenerationResult:
        """Generate an assistant response to a new user message."""
        self._validate_message(content, generation_options)

        self._conversation.add_user_message(content)

        request = self._build_request(generation_options)

        result = self._runtime.generate(request)

        if not result.done:
            raise RuntimeError(
                "Generation is incomplete; assistant response was not stored."
            )

        self._conversation.add_assistant_message(result.text)

        return result

    def stream_message(
        self,
        content: str,
        **generation_options: Any,
    ) -> Iterator[StreamEvent]:
        """Stream an assistant response and store it only after successful completion."""
        self._validate_message(content, generation_options)

        if generation_options.get("stream", True) is not True:
            raise ValueError("stream_message requires stream=True.")

        options = {
            **generation_options,
            "stream": True,
        }

        self._conversation.add_user_message(content)

        request: GenerationRequest = self._build_request(options)

        collected_text: list[str] = []
        final_result: GenerationResult | None = None
        runtime_stream: Iterator[StreamEvent] | None = None

        try:
            runtime_stream = self._runtime.generate_stream(request)

            for event in runtime_stream:
                if event.is_final:
                    final_result = event.final_metadata

                    if final_result is None or not final_result.done:
                        raise RuntimeStreamingError(
                            "Streaming ended without valid completion metadata."
                        )

                if event.text_delta:
                    collected_text.append(event.text_delta)

                yield event

            if final_result is None:
                raise RuntimeStreamingError(
                    "Streaming ended without a final completion event."
                )

            response_text = "".join(collected_text)

            if response_text != final_result.text:
                raise RuntimeStreamingError(
                    "Streamed text does not match final generation metadata."
                )

            self._conversation.add_assistant_message(response_text)

        finally:
            if runtime_stream is not None:
                close = getattr(runtime_stream, "close", None)

                if callable(close):
                    close()

    @staticmethod
    def _validate_message(
        content: str,
        generation_options: dict[str, Any],
    ) -> None:
        """Validate user input and prevent prompt overrides."""
        if not isinstance(content, str) or not content.strip():
            raise ValueError("User message must not be empty or whitespace-only.")

        if "prompt" in generation_options:
            raise ValueError("The prompt must be generated from conversation messages.")
