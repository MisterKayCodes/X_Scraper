"""
Handlers Package — Import all routers here.
"""
from aiogram import Router
from .menu import router as menu_router
from .harvest import router as harvest_router
from .stats import router as stats_router
from .settings import router as settings_router
from .sources import router as sources_router
from .targets import router as targets_router
from .scraper_handlers import router as scraper_router
from .target_handlers import router as target_handlers_router
from .yt_handlers import router as yt_router
from app.bot.callbacks import router as callbacks_router

def register_handlers() -> Router:
    """Register all handlers into one main router."""
    main_router = Router()
    main_router.include_router(menu_router)
    main_router.include_router(harvest_router)
    main_router.include_router(stats_router)
    main_router.include_router(settings_router)
    main_router.include_router(sources_router)
    main_router.include_router(targets_router)
    main_router.include_router(scraper_router)
    main_router.include_router(target_handlers_router)
    main_router.include_router(yt_router)
    main_router.include_router(callbacks_router)
    return main_router