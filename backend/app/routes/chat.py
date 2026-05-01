from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.retriever import query_document

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    collection_name: str
    # History is a list of [question, answer] pairs from the conversation so far
    chat_history: list[tuple[str, str]] = []


@router.post("/")
async def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    try:
        result = query_document(
            question=request.question,
            collection_name=request.collection_name,
            chat_history=request.chat_history,
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"Query failed: {str(e)}")
