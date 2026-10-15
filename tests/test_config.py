"""Tests for centralized runtime configuration."""

import pytest
from pydantic import ValidationError

from app.config import RuntimeSettings, load_settings


def test_default_settings() -> None:
    """Verify the project's default configuration."""

    settings = load_settings(environ={})

    assert settings.ollama_host == "http://127.0.0.1:11434"
    assert settings.model_name == "qwen3.8:27b"
    assert settings.request_timeout_seconds == 120.0
    assert settings.keep_alive == "5m"
    assert settings.num_ctx == 4096
    assert settings.max_new_tokens == 16
    assert settings.temperature == 0.0

    assert settings.top_k is None
    assert settings.top_p is None
    assert settings.seed is None


def test_environment_overrides() -> None:
    """Verify that explicit environment values override defaults."""

    settings = load_settings(
        environ={
            "OLLAMA_HOST": "http://localhost:11434",
            "MODEL_NAME": "qwen3.8:27b",
            "REQUEST_TIMEOUT_SECONDS": "45",
            "NUM_CTX": "4096",
            "MAX_NEW_TOKENS": "24",
            "TEMPERATURE": "0.2",
            "TOP_K": "20",
            "TOP_P": "0.9",
            "SEED": "42",
        }
    )

    assert settings.ollama_host == "http://localhost:11434"
    assert settings.request_timeout_seconds == 45.0
    assert settings.num_ctx == 4096
    assert settings.max_new_tokens == 24
    assert settings.temperature == 0.2
    assert settings.top_k == 20
    assert settings.top_p == 0.9
    assert settings.seed == 42


def test_env_file_and_environment_precedence(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that process environment values override values from .env."""

    environment_keys = [
        "OLLAMA_HOST",
        "MODEL_NAME",
        "REQUEST_TIMEOUT_SECONDS",
        "KEEP_ALIVE",
        "NUM_CTX",
        "MAX_NEW_TOKENS",
        "TEMPERATURE",
        "TOP_K",
        "TOP_P",
        "SEED",
    ]

    # Remove potentially conflicting settings from the current process.
    for key in environment_keys:
        monkeypatch.delenv(key, raising=False)

    env_file = tmp_path / ".env"

    env_file.write_text(
        "\n".join(
            [
                "OLLAMA_HOST=http://localhost:11434",
                "MODEL_NAME=qwen3.8:27b",
                "MAX_NEW_TOKENS=20",
            ]
        ),
        encoding="utf-8",
    )

    # The operating-system environment must take precedence over .env.
    monkeypatch.setenv("MAX_NEW_TOKENS", "32")

    settings = load_settings(env_file=env_file)

    assert settings.ollama_host == "http://localhost:11434"
    assert settings.model_name == "qwen3.8:27b"
    assert settings.max_new_tokens == 32


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("request_timeout_seconds", 0),
        ("request_timeout_seconds", -1),
        ("num_ctx", 0),
        ("max_new_tokens", 0),
        ("max_new_tokens", 513),
        ("temperature", -0.1),
        ("temperature", 2.1),
        ("top_k", 0),
        ("top_p", -0.1),
        ("top_p", 1.1),
        ("seed", -1),
    ],
)
def test_invalid_numeric_values_are_rejected(
    field_name: str,
    invalid_value: int | float,
) -> None:
    """Reject numeric settings that violate the configuration policy."""

    with pytest.raises(ValidationError):
        RuntimeSettings(**{field_name: invalid_value})


@pytest.mark.parametrize(
    "invalid_host",
    [
        "localhost:11434",
        "ftp://localhost:11434",
        "http://",
        "http://localhost:70000",
        "http://user:password@localhost:11434",
        "http://localhost:11434/api",
    ],
)
def test_invalid_ollama_hosts_are_rejected(
    invalid_host: str,
) -> None:
    """Reject URLs that violate the configured Ollama base URL policy."""

    with pytest.raises(ValidationError):
        RuntimeSettings(ollama_host=invalid_host)


@pytest.mark.parametrize(
    "invalid_model_name",
    [
        "",
        " ",
        " qwen3.8:27b",
        "qwen3.8:27b ",
    ],
)
def test_invalid_model_names_are_rejected(
    invalid_model_name: str,
) -> None:
    """Reject empty model identifiers and surrounding whitespace."""

    with pytest.raises(ValidationError):
        RuntimeSettings(model_name=invalid_model_name)


def test_unknown_configuration_fields_are_rejected() -> None:
    """Reject unsupported fields rather than silently accepting them."""

    with pytest.raises(ValidationError):
        RuntimeSettings(unsupported_option="unexpected")
