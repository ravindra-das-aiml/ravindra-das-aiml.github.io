from fastapi import APIRouter, HTTPException, Request

from app.core.rate_limit import limiter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.groq_client import GroqServiceError, generate_reply


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    try:
        reply = await generate_reply(payload.messages)
    except GroqServiceError as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.public_message,
        ) from error
    return ChatResponse(reply=reply)
