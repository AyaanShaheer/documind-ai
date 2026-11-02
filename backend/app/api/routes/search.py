
import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from app.core.auth import get_current_user_id

from opensearchpy.exceptions import OpenSearchException

from app.schemas.search import (
    SearchRequest,
    SearchResponse,
)

from app.services.search_service import semantic_search


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=SearchResponse,
)
async def search_documents(

    request: SearchRequest,

    user_id: str = Depends(get_current_user_id),
):

    try:

        results = semantic_search(
            question=request.question,
            user_id=user_id,
            top_k=request.top_k,
        )

        return SearchResponse(
            query=request.question,
            count=len(results),
            results=results,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except OpenSearchException as exc:

        logger.exception("OpenSearch query failed")

        raise HTTPException(
            status_code=503,
            detail="Search service temporarily unavailable",
        ) from exc

    except Exception as exc:

        logger.exception("Unexpected search failure")

        raise HTTPException(
            status_code=500,
            detail="Unable to complete search",
        ) from exc

