from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite import SqliteSaver

from app.api.routes import router
from app.core.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION, CHECKPOINT_DB_PATH
from app.services.graph_builder import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    checkpointer_cm = SqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
    checkpointer = checkpointer_cm.__enter__()
    app.state.checkpointer_cm = checkpointer_cm
    app.state.graph = build_graph(checkpointer=checkpointer)
    yield
    checkpointer_cm.__exit__(None, None, None)


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)
app.include_router(router)
