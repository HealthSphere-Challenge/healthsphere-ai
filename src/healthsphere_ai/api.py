"""FastAPI application implementing the authoritative HS-002 transport contract."""

from __future__ import annotations

import hmac
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from healthsphere_ai.artifacts import ArtifactError, ModelBundle
from healthsphere_ai.inference import InferenceExecutionError, InferenceService
from healthsphere_ai.schemas import ErrorDetail, ErrorResponse, InferenceRequest, InferenceResponse

LOGGER = logging.getLogger("healthsphere_ai")
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "artifacts/hypertension_5y/v1"


def _error(
    status_code: int,
    code: str,
    message: str,
    request_id: UUID | None = None,
    details: list[dict[str, object]] | None = None,
) -> JSONResponse:
    content = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details,
            request_id=request_id,
            retry_after_seconds=None,
        )
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=content)


def create_app(
    artifact_dir: Path | None = None,
    internal_api_token: str | None = None,
    bundle: ModelBundle | None = None,
) -> FastAPI:
    directory = artifact_dir or Path(
        os.environ.get("HEALTHSPHERE_ARTIFACT_DIR", DEFAULT_ARTIFACT_DIR)
    )
    configured_token = internal_api_token or os.environ.get("HEALTHSPHERE_INTERNAL_API_TOKEN")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not configured_token:
            raise RuntimeError("HEALTHSPHERE_INTERNAL_API_TOKEN is required.")
        loaded = bundle or ModelBundle.load(directory)
        app.state.inference_service = InferenceService(loaded)
        app.state.model_ready = True
        LOGGER.info("model_ready model_version=%s", loaded.metadata["model_version"])
        yield

    app = FastAPI(title="HealthSphere AI", version="0.1.0", lifespan=lifespan)
    app.state.model_ready = False

    async def authorize(authorization: str | None = Header(default=None)) -> None:
        expected = f"Bearer {configured_token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            from fastapi import HTTPException

            raise HTTPException(status_code=401, detail="unauthorized")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"location": ".".join(str(part) for part in error["loc"]), "type": error["type"]}
            for error in exc.errors()
        ]
        request_id = None
        try:
            candidate = (await request.json()).get("request_id")
            parsed = UUID(candidate) if isinstance(candidate, str) else None
            request_id = parsed if parsed is not None and parsed.version == 4 else None
        except (ValueError, AttributeError):
            pass
        return _error(
            422,
            "validation_error",
            "The inference request could not be validated.",
            request_id=request_id,
            details=details,
        )

    from fastapi import HTTPException

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 401:
            return _error(401, "unauthorized", "Service authentication failed.")
        if exc.detail == "request_id_mismatch":
            return _error(422, "request_id_mismatch", "Request correlation IDs do not match.")
        return _error(exc.status_code, "request_error", "The request could not be processed.")

    @app.exception_handler(ArtifactError)
    async def artifact_error(_request: Request, _exc: ArtifactError) -> JSONResponse:
        LOGGER.exception("artifact_unavailable")
        return _error(503, "model_unavailable", "The model is unavailable.")

    @app.get("/health")
    async def health(request: Request) -> dict[str, object]:
        return {"status": "ready" if request.app.state.model_ready else "not_ready"}

    @app.post(
        "/internal/v1/inferences",
        response_model=InferenceResponse,
        dependencies=[Depends(authorize)],
    )
    async def inference(
        payload: InferenceRequest,
        request: Request,
        x_request_id: Annotated[UUID, Header(alias="X-Request-ID")],
    ) -> InferenceResponse:
        if x_request_id.version != 4 or x_request_id != payload.request_id:
            raise HTTPException(status_code=422, detail="request_id_mismatch")
        try:
            return request.app.state.inference_service.predict(payload)
        except InferenceExecutionError:
            LOGGER.exception("inference_unavailable request_id=%s", payload.request_id)
            return InferenceResponse(
                request_id=payload.request_id,
                status="unavailable",
                result=None,
                reason={"code": "inference_unavailable", "missing_fields": None},
                provenance=None,
            )

    return app


app = create_app()
