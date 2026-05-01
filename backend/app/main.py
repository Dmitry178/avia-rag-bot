from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.core.config import settings
from app.core.lifespan import lifespan
from app.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    """
    Build and configure FastAPI application.
    """

    app = FastAPI(
        title=settings.app.title,
        description=settings.app.description,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app.cors_origins,
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS"
        ],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Type",
            "Authorization",
            "X-Request-ID",
        ],
    )
    register_exception_handlers(app)
    app.include_router(router)

    return app


app = create_app()
