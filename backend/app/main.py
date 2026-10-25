from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.data.database import init_db
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down application...")

def create_app(custom_settings=None) -> FastAPI:
    cfg = custom_settings or settings

    # Startup validation: Fail clearly on unsafe CORS settings
    if cfg.CORS_ALLOW_CREDENTIALS:
        if any(origin == "*" or origin.strip() == "*" for origin in cfg.CORS_ORIGINS):
            raise ValueError(
                "Insecure CORS configuration: Wildcard '*' origin is prohibited when allow_credentials=True."
            )

    application = FastAPI(
        title=cfg.PROJECT_NAME,
        description="Production-Quality UK Wind Generation Forecast Accuracy Dashboard for Day-Ahead Power Traders.",
        version="1.0.0",
        lifespan=lifespan
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.CORS_ORIGINS,
        allow_credentials=cfg.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(router, prefix=cfg.API_V1_STR)

    @application.get("/")
    def root():
        return {
            "name": cfg.PROJECT_NAME,
            "version": "1.0.0",
            "description": "UK Wind Generation Forecast Accuracy Analytics Terminal",
            "docs_url": "/docs",
            "health_check": f"{cfg.API_V1_STR}/health",
            "evaluation_endpoint": f"{cfg.API_V1_STR}/evaluation"
        }

    return application

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
