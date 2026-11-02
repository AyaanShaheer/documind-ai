
import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user_id

from opensearchpy.exceptions import OpenSearchException

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)

from app.services.rag_service import (
    RAGServiceError,
    generate_rag_answer,
)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    response_model=ChatResponse,
)
def chat_with_documents(

    request: ChatRequest,

    user_id: str = Depends(get_current_user_id),
):

    try:

        result = generate_rag_answer(
            question=request.question,
            user_id=user_id,
            top_k=request.top_k,
        )

        return ChatResponse(
            question=request.question,
            answer=result["answer"],
            model=result["model"],
            retrieved_chunks=result["retrieved_chunks"],
            sources=result["sources"],
        )

    except RAGServiceError as exc:

        logger.exception("RAG generation failed")

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except OpenSearchException as exc:

        logger.exception("OpenSearch retrieval failed")

        raise HTTPException(
            status_code=503,
            detail="Document retrieval service unavailable",
        ) from exc

    except Exception as exc:

        logger.exception("Unexpected chat error")

        raise HTTPException(
            status_code=500,
            detail="Unable to process your question",
        ) from exc
