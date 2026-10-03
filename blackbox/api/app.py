from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from blackbox.api import (
    auth,
    business,
    compare,
    demo,
    eval,
    fleet,
    health,
    lab,
    replay,
    runs,
)
from blackbox.api.common import mock_mode
from blackbox.config import get_settings
from blackbox.notify.scheduler import scheduler
from blackbox.notify.worker import worker
from blackbox.store.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not mock_mode():
        init_db()
        worker.start()
        scheduler.start()
    try:
        yield
    finally:
        if not mock_mode():
            scheduler.stop()
            worker.stop()


app = FastAPI(title="Black Box", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_demo_session(request: Request, call_next):
    settings = get_settings()
    public_path = request.url.path.startswith("/api/auth/")
    if (
        not settings.DEMO_AUTH_ENABLED
        or mock_mode()
        or request.method == "OPTIONS"
        or public_path
    ):
        return await call_next(request)
    if auth.authenticated_email(request) is None:
        return JSONResponse(status_code=401, content={"detail": "Not signed in"})
    return await call_next(request)

for api_router in (
    auth.router,
    demo.router,
    runs.router,
    replay.router,
    compare.router,
    eval.router,
    fleet.router,
    lab.router,
    health.router,
    business.router,
):
    app.include_router(api_router, prefix="/api")