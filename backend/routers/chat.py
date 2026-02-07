from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse
from services.rag_service import RAGService

router = APIRouter()
rag_service = None


def get_rag_service() -> RAGService:
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        service = get_rag_service()
        result = await service.process_query(
            message=request.message,
            conversation_history=request.conversation_history or [],
            page_url=request.page_url
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
