from fastapi import FastAPI

from app.core.config import settings
from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.search import router as search_router
from app.api.routes.chat import router as chat_router
from app.api.routes import session


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

app.include_router(
    search_router,
    prefix="/api/v1/search",
    tags=["Search"],
)

app.include_router(
    chat_router,
    prefix="/api/v1/chat",
    tags=["Chat"],
)

app.include_router(session.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to DocuMind AI",
        "status": "running",
    }
