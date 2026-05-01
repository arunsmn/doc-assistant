from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agents.router import (
    route_query,
    answer_general_question,
    ROUTE_RAG,
    ROUTE_LLM,
    ROUTE_REJECT,
)
from app.services.retriever import query_document

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    collection_name: str
    chat_history: list[tuple[str, str]] = []


# These messages are shown to the user in the frontend
REJECT_MESSAGE = (
    "I'm a document assistant — I can only help with questions about "
    "your uploaded documents or general knowledge questions. "
    "I can't help with that request."
)


@router.post("/")
async def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    try:
        # ── Step 1: Route the query ───────────────────────────────────────
        route = route_query(request.question)
        print(f"Query routed to: {route}")  # visible in your terminal logs

        # ── Step 2: Execute the right tool ───────────────────────────────
        if route == ROUTE_REJECT:
            return {"answer": REJECT_MESSAGE, "sources": [], "route": ROUTE_REJECT}

        elif route == ROUTE_LLM:
            answer = answer_general_question(
                question=request.question, chat_history=request.chat_history
            )
            return {
                "answer": answer,
                "sources": [],  # no document sources for general questions
                "route": ROUTE_LLM,
            }

        else:  # ROUTE_RAG
            result = query_document(
                question=request.question,
                collection_name=request.collection_name,
                chat_history=request.chat_history,
            )
            return {
                "answer": result["answer"],
                "sources": result["sources"],
                "route": ROUTE_RAG,  # frontend can use this to show/hide source cards
            }

    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")
