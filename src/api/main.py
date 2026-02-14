"""FastAPI app entrypoint for budget-mode backend skeleton."""

from fastapi import FastAPI

from src.api.routers.chat import router as chat_router
from src.api.routers.health import router as health_router
from src.api.routers.search import router as search_router
from src.api.routers.stats import router as stats_router
from src.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(search_router, prefix=settings.api_prefix)
app.include_router(stats_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)

