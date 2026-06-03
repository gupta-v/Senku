import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from SenkuNoChinou.controllers.api import router as senku_router
from SenkuNoChinou.core.workflow import build_workflow
from SenkuNoChinou.services.stt import STTService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stt = STTService(
        model_size=os.getenv("WHISPER_MODEL", "small"),
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
        model_dir=os.getenv("WHISPER_MODEL_DIR"),  # None → default models/stt_models/
    )
    async with build_workflow() as workflow:
        app.state.workflow = workflow
        yield


app = FastAPI(title="SenkuNoChinou", lifespan=lifespan)
app.include_router(senku_router)


