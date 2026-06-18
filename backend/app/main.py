from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import analysis, health
from .ai_services.warmup import start_warmup_in_background
from .core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load enabled AI models in the background so the first uploaded video
    # does not pay the model-load cost during analysis.
    start_warmup_in_background()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)
app.include_router(analysis.router)
