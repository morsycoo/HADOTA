"""Conversation orchestration service for the Local AI Assistant."""

from collections.abc import Iterator
from typing import Any

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
    ) -> None:
        self._runtime = runtime
        self._conversation = conversation
        self._prompt_builder = prompt_builder

    @property
    def conversation(self) -> ConversationManager:
        """Expose the managed conversation."""
        return self._conversation

    def send_message(
        self,
        content: str,
        **generation_options: Any,
    ) -> GenerationResult:
        """Generate an assistant response to a new user message."""
        self._validate_message(content, generation_options)

        self._conversation.add_user_message(content)

        request = self._prompt_builder.build_request(
            self._conversation.get_messages(),
            **generation_options,
        )

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

        self._conversation.add_user_message(content)

        request: GenerationRequest = self._prompt_builder.build_request(
            self._conversation.get_messages(),
            stream=True,
            **generation_options,
        )

        collected_text: list[str] = []
        final_result: GenerationResult | None = None

        try:
            for event in self._runtime.generate_stream(request):
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

        except RuntimeStreamingError:
            raise

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
