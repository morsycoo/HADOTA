"""Ollama runtime adapter for the Local AI Assistant."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import RuntimeSettings, load_settings
from app.runtime.exceptions import (
    RuntimeConnectionError,
    RuntimeHTTPError,
    RuntimeResponseError,
    RuntimeTimeoutError,
)


class OllamaRuntime:
    """HTTP adapter for the local Ollama runtime."""

    def __init__(
        self,
        settings: RuntimeSettings | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings or load_settings()
        self._owns_client = client is None

        self._client = client or httpx.Client(
            timeout=self.settings.request_timeout_seconds,
        )

    def close(self) -> None:
        """Close the HTTP client when it is owned by this adapter."""

        if self._owns_client:
            self._client.close()

    def __enter__(self) -> OllamaRuntime:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _get_json(self, endpoint: str) -> dict[str, Any]:
        """Send a GET request and validate the basic JSON response shape."""

        url = f"{self.settings.ollama_host}{endpoint}"

        try:
            response = self._client.get(url)

        except httpx.TimeoutException as error:
            raise RuntimeTimeoutError(
                "The Ollama request exceeded its configured timeout."
            ) from error

        except httpx.RequestError as error:
            raise RuntimeConnectionError(
                "The Ollama service could not be reached."
            ) from error

        try:
            response.raise_for_status()

        except httpx.HTTPStatusError as error:
            raise RuntimeHTTPError(
                "The Ollama service returned an unsuccessful HTTP status.",
                status_code=error.response.status_code,
            ) from error

        try:
            payload = response.json()

        except ValueError as error:
            raise RuntimeResponseError(
                "The Ollama service returned invalid JSON."
            ) from error

        if not isinstance(payload, dict):
            raise RuntimeResponseError("The Ollama response must be a JSON object.")

        return payload

    def health(self) -> bool:
        """Return True when the Ollama version endpoint responds correctly."""

        payload = self._get_json("/api/version")
        version = payload.get("version")

        if not isinstance(version, str) or not version.strip():
            raise RuntimeResponseError(
                "The Ollama version response is missing a valid version."
            )

        return True

    def list_models(self) -> list[str]:
        """Return model identifiers reported by the Ollama inventory endpoint."""

        payload = self._get_json("/api/tags")
        models = payload.get("models")

        if not isinstance(models, list):
            raise RuntimeResponseError(
                "The Ollama model inventory does not contain a valid model list."
            )

        model_names: list[str] = []

        for item in models:
            if not isinstance(item, dict):
                raise RuntimeResponseError(
                    "The Ollama model inventory contains an invalid entry."
                )

            name = item.get("name")

            if not isinstance(name, str) or not name.strip():
                raise RuntimeResponseError(
                    "The Ollama model inventory contains an invalid model name."
                )

            model_names.append(name)

        return model_names
