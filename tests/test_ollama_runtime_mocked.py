"""Mocked tests for the Ollama runtime adapter."""

import json

import httpx
import pytest

from app.config import RuntimeSettings
from app.runtime.exceptions import (
    RuntimeConnectionError,
    RuntimeHTTPError,
    RuntimeResponseError,
    RuntimeTimeoutError,
)
from app.runtime.ollama_runtime import OllamaRuntime


def make_runtime(handler):
    """Create an adapter backed by a mocked HTTP transport."""

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
    )

    settings = RuntimeSettings(
        ollama_host="http://test-server",
        model_name="qwen3.8:27b",
    )

    runtime = OllamaRuntime(
        settings=settings,
        client=client,
    )

    return runtime, client


def test_health_success() -> None:
    """Accept a valid version response."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/version"

        return httpx.Response(
            200,
            json={"version": "0.35.1"},
        )

    runtime, client = make_runtime(handler)

    try:
        assert runtime.health() is True
    finally:
        client.close()


def test_health_rejects_missing_version() -> None:
    """Reject a successful response with an invalid version payload."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    runtime, client = make_runtime(handler)

    try:
        with pytest.raises(RuntimeResponseError):
            runtime.health()
    finally:
        client.close()


def test_list_models_success() -> None:
    """Return model identifiers from the inventory response."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tags"

        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "qwen3.8:27b"},
                    {"name": "example-model:latest"},
                ]
            },
        )

    runtime, client = make_runtime(handler)

    try:
        assert runtime.list_models() == [
            "qwen3.8:27b",
            "example-model:latest",
        ]
    finally:
        client.close()


def test_list_models_empty_inventory() -> None:
    """Accept a valid inventory containing no models."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"models": []},
        )

    runtime, client = make_runtime(handler)

    try:
        assert runtime.list_models() == []
    finally:
        client.close()


def test_list_models_rejects_invalid_payload() -> None:
    """Reject an inventory response without a models list."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"unexpected": []},
        )

    runtime, client = make_runtime(handler)

    try:
        with pytest.raises(RuntimeResponseError):
            runtime.list_models()
    finally:
        client.close()


def test_http_error_is_normalized() -> None:
    """Preserve the HTTP status in the runtime exception."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            json={"error": "Service unavailable"},
        )

    runtime, client = make_runtime(handler)

    try:
        with pytest.raises(RuntimeHTTPError) as captured:
            runtime.health()

        assert captured.value.status_code == 503
    finally:
        client.close()


def test_timeout_is_normalized() -> None:
    """Translate a timeout into the runtime timeout exception."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            "Simulated timeout",
            request=request,
        )

    runtime, client = make_runtime(handler)

    try:
        with pytest.raises(RuntimeTimeoutError):
            runtime.health()
    finally:
        client.close()


def test_connection_error_is_normalized() -> None:
    """Translate a connection failure into a runtime connection exception."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            "Simulated connection failure",
            request=request,
        )

    runtime, client = make_runtime(handler)

    try:
        with pytest.raises(RuntimeConnectionError):
            runtime.health()
    finally:
        client.close()


def test_invalid_json_is_normalized() -> None:
    """Translate an invalid JSON response into a runtime response error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"{invalid-json",
            headers={"Content-Type": "application/json"},
        )

    runtime, client = make_runtime(handler)

    try:
        with pytest.raises(RuntimeResponseError):
            runtime.health()
    finally:
        client.close()
