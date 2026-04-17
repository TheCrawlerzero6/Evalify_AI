from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver

from app.config import (
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    CHECKPOINT_DB_PATH,
    CORS_ALLOW_ORIGINS,
    LOG_FORMAT,
    LOG_LEVEL,
)
from app.routes import router
from app.services.graph_builder import build_graph

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando recursos de aplicacion")
    checkpointer_cm = None
    checkpointer_entered = False
    try:
        checkpointer_cm = SqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
        checkpointer = checkpointer_cm.__enter__()
        checkpointer_entered = True
        app.state.checkpointer_cm = checkpointer_cm
        app.state.graph = build_graph(checkpointer=checkpointer)
        logger.info("Recursos inicializados correctamente db_path=%s", CHECKPOINT_DB_PATH)
        yield
    except Exception as exc:
        logger.exception("Error durante el ciclo de vida de la aplicacion", exc_info=exc)
        raise
    finally:
        if checkpointer_cm is not None and checkpointer_entered:
            logger.info("Liberando recursos de aplicacion")
            checkpointer_cm.__exit__(None, None, None)
        logger.info("Recursos de aplicacion liberados")


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
