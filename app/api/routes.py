from fastapi import APIRouter
from pydantic import BaseModel
from app.chatbot.rag_chain import ask_question

router = APIRouter()

# 1. Define the input structure matching the JavaScript body
class ChatRequest(BaseModel):
    question: str

# 2. Use the ChatRequest model in your POST endpoint
@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Pass request.question into your RAG logic
    result = ask_question(request.question)
    return result