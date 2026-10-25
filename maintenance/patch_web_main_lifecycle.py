from pathlib import Path
import shutil

path = Path("app/web/main.py")
backup = Path("app/web/main.py.pre_shared_runtime.bak")

if backup.exists():
    raise SystemExit(
        f"Backup already exists: {backup}. No changes made."
    )

content = path.read_text(encoding="utf-8")

if "def create_app(" not in content or '"/api/health"' not in content:
    raise SystemExit(
        "main.py does not match the expected version. No changes made."
    )

new_content = '''"""FastAPI application entry point for HADOTA."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.cli import (
    create_conversation_service,
    create_conversation_service_with_runtime,
)
from app.config import load_settings
from app.runtime.exceptions import RuntimeErrorBase
from app.runtime.ollama_runtime import OllamaRuntime
from app.web.sessions import SessionManager

ServiceFactory = Callable[..., tuple[Any, Any]]


def create_app(
    service_factory: ServiceFactory | None = None,
) -> FastAPI:
    """Create the HADOTA API application."""

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        runtime = None
        session_manager = None

        try:
            if service_factory is None:
                settings = load_settings()
                runtime = OllamaRuntime(settings=settings)
                session_manager = SessionManager()

                application.state.runtime = runtime
                application.state.session_manager = session_manager
                application.state.settings = settings
                application.state.create_conversation_service = (
                    lambda: create_conversation_service_with_runtime(runtime)
                )
            else:
                # Preserve compatibility with the original injected factory.
                runtime, service = service_factory()
                application.state.runtime = runtime
                application.state.conversation_service = service
                application.state.session_manager = SessionManager()

            yield
        finally:
            if session_manager is not None:
                session_manager.cleanup_expired()

                # Remove remaining in-memory sessions and close their services.
                with session_manager._lock:
                    session_ids = list(session_manager._sessions)

                for session_id in session_ids:
                    session_manager.delete_session(session_id)

            application.state.runtime = None
            application.state.session_manager = None

            if hasattr(application.state, "settings"):
                application.state.settings = None

            if hasattr(application.state, "create_conversation_service"):
                application.state.create_conversation_service = None

            if hasattr(application.state, "conversation_service"):
                application.state.conversation_service = None

            if runtime is not None:
                runtime.close()

    application = FastAPI(
        title="HADOTA — Local AI Assistant",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @application.get("/api/health")
    async def health(request: Request) -> JSONResponse:
        """Return a minimal health status without exposing runtime details."""

        runtime = getattr(request.app.state, "runtime", None)

        if runtime is None:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable"},
            )

        try:
            available = runtime.health()
        except RuntimeErrorBase:
            available = False

        if not available:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable"},
            )

        return JSONResponse(
            status_code=200,
            content={"status": "ok"},
        )

    return application


app = create_app()
'''

shutil.copy2(path, backup)
path.write_text(new_content, encoding="utf-8")

print(f"Updated {path}")
print(f"Backup saved to {backup}")
