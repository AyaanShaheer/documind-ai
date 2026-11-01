
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():

    return {
        "application": "DocuMind AI",
        "status": "healthy",
        "environment": "local"
    }

