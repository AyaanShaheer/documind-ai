from fastapi import FastAPI

from app.core.config import settings
from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router


app = FastAPI(
    title=settings.app_name,
    description="Cloud-native AI Document Intelligence Platform",
    version="0.2.0",
)


app.include_router(
    health_router,
    prefix="/api/v1",
    tags=["Health"],
)

app.include_router(
    documents_router,
    prefix="/api/v1/documents",
    tags=["Documents"],
)


@app.get("/")
async def root():

    return {
        "message": "Welcome to DocuMind AI",
        "status": "running",
    }
