from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import models
from .auth import router
from .config import settings
from .database import Base, create_database_engine, create_session_factory


def create_app(database_url: str | None = None, auto_create_tables: bool | None = None) -> FastAPI:
    engine = create_database_engine(database_url or settings.database_url)
    create_tables = settings.auto_create_tables if auto_create_tables is None else auto_create_tables

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if create_tables:
            Base.metadata.create_all(bind=engine)
        yield
        engine.dispose()

    application = FastAPI(title="SmartCampus AI API", version="1.0.0", lifespan=lifespan)
    application.state.engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.include_router(router)

    @application.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": "SmartCampus AI API",
            "status": "running",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    @application.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @application.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        title_by_status = {401: "Authentification requise", 403: "Accès refusé", 404: "Ressource introuvable"}
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": title_by_status.get(exc.status_code, "Requête refusée"),
                "status": exc.status_code,
                "detail": exc.detail,
                "code": "permission_denied" if exc.status_code == 403 else "request_rejected",
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": "Données invalides",
                "status": 422,
                "detail": "La requête ne respecte pas le contrat de l'API.",
                "code": "validation_error",
                "request_id": getattr(request.state, "request_id", None),
                "errors": errors,
            },
        )

    return application


app = create_app()