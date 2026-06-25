from __future__ import annotations

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import db_ping, init_schema
from app.middleware import InMemoryRateLimitMiddleware
from app.routers import licenses, releases, admin

settings = get_settings()

app = FastAPI(
    title="Boxio License Server",
    version="1.0.1",
    description="API HTTPS para ativação, validação e gestão de licenças do Boxio.",
)

origins = ["*"] if settings.cors_origins == "*" else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.rate_limit_enabled:
    app.add_middleware(InMemoryRateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)


@app.on_event("startup")
def startup():
    # No Render, o health check principal deve confirmar se a aplicação FastAPI
    # subiu. A conexão com o Neon é validada separadamente em /health/db.
    #
    # Se o Neon estiver temporariamente indisponível ou se ainda houver ajuste de
    # permissão no banco, o app continua acessível para diagnóstico em /health e
    # /health/db, em vez de ficar preso na tela "Application Loading".
    try:
        init_schema()
        app.state.startup_db_error = None
    except Exception as exc:
        app.state.startup_db_error = str(exc)


app.include_router(licenses.router)
app.include_router(releases.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "boxio-license-server",
        "environment": settings.app_env,
        "docs": "/docs",
        "health": "/health",
        "database_health": "/health/db",
    }


@app.get("/health")
def health():
    db_startup_error = getattr(app.state, "startup_db_error", None)
    return {
        "ok": True,
        "service": "boxio-license-server",
        "environment": settings.app_env,
        "schema": settings.db_schema,
        "database_startup": "ok" if not db_startup_error else "error",
        "database_health": "/health/db",
    }


@app.get("/health/db")
def health_db():
    try:
        db_ping()
        startup_error = getattr(app.state, "startup_db_error", None)
        if startup_error:
            try:
                init_schema()
                app.state.startup_db_error = None
            except Exception as exc:
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "ok": False,
                        "service": "boxio-license-server",
                        "database": "error",
                        "message": str(exc),
                    },
                )

        return {"ok": True, "service": "boxio-license-server", "database": "ok"}
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"ok": False, "service": "boxio-license-server", "database": "error", "message": str(exc)},
        )
