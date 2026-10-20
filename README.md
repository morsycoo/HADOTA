# HADOTA - Local AI Assistant

> **HADOTA** takes its name from the Egyptian Arabic word for a story or tale. Inspired by the idea of a curious storyteller with a wealth of knowledge, HADOTA "حدوته" aims to be a local AI companion for exploring ideas, learning new things, and discussing a wide range of topics.

🚧 **Status: In active development** — this README is a temporary overview and will evolve as the project grows.

HADOTA is being built around a locally running language model, with an emphasis on understanding and engineering the full LLM application pipeline—from generation and prompt construction to conversation management and structured responses.

## Current Capabilities

- **Local inference:** Connects to a local Qwen model through Ollama.
- **Generation runtime:** Supports non-streaming and streaming responses through a dedicated runtime adapter.
- **Conversation management:** Maintains conversation history and builds prompts for generation.
- **Context management:** Selects recent conversation content to fit a configurable prompt-token budget.
- **Structured output:** Supports JSON mode, JSON Schema, and Pydantic-based response validation.
- **Engineering tests:** Includes unit, mocked-runtime, and local-runtime integration tests.
- **LLM fundamentals:** Documents experiments with tokenization, decoding strategies, generation metadata, and runtime performance.

## Tech Stack

- Python
- Ollama
- Qwen local language model
- PyTorch and Hugging Face tokenizer tooling
- Pydantic, HTTPX, and Pytest

## Run Tests

With the project environment configured and dependencies installed, run the test suite from the repository root:

```bash
python -m pytest .\tests -q
```

The latest recorded test run passed **212 tests with 0 failures**. Results may change as development continues.

## Project Direction

HADOTA is a work in progress. The next stages will expand the assistant experience and strengthen prompt design, evaluation, and application orchestration.

---

*More details, setup instructions, and usage examples will be added as the project approaches its first complete release.*
