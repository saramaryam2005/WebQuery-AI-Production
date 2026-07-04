from fastapi import APIRouter

from app.api.models import ChatRequest, ChatResponse
from app.chatbot.rag_chain import ask_question

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = ask_question(request.question)

    return ChatResponse(
        answer=result["answer"]
    )