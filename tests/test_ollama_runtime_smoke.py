"""Real integration smoke tests for the Ollama runtime adapter."""

from app.config import load_settings
from app.runtime.ollama_runtime import OllamaRuntime
from app.schemas import GenerationRequest


def test_real_ollama_non_streaming_smoke() -> None:
    """Verify non-streaming generation against the running local Ollama service."""

    settings = load_settings()

    with OllamaRuntime(settings=settings) as runtime:
        # Verify service availability.
        assert runtime.health() is True

        # Verify that the configured model is available.
        available_models = runtime.list_models()

        assert settings.model_name in available_models, (
            f"Configured model '{settings.model_name}' "
            f"was not found. Available models: {available_models}"
        )

        # Execute one short, real-model generation request.
        request = GenerationRequest(
            prompt=(
                "Explain what an LLM runtime does in one sentence. "
                "Answer directly and do not include a reasoning section."
            ),
            stream=False,
            max_new_tokens=64,
        )

        result = runtime.generate(request)

    # Validate the normalized result after the runtime client is closed.
    assert isinstance(result.text, str)
    assert result.text.strip(), "The runtime returned empty generated text."

    assert result.model == settings.model_name
    assert result.done is True

    assert result.client_latency_ms is not None
    assert result.client_latency_ms >= 0

    # Display actual observations for this integration test.
    print(f"\nRuntime model: {result.model}")
    print(f"Generated text: {result.text}")
    print(f"Runtime completion reason: {result.done_reason}")
    print(f"Prompt token count: {result.prompt_eval_count}")
    print(f"Generated token count: {result.eval_count}")
    print(f"Client latency (ms): {result.client_latency_ms:.2f}")
    print(f"Runtime total duration (ns): {result.total_duration_ns}")
