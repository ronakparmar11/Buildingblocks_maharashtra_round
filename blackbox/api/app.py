from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from blackbox.api import business, compare, eval, fleet, health, lab, replay, runs
from blackbox.api.common import mock_mode
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

for api_router in (
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