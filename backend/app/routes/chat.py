import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.agents.router import (
    route_query,
    answer_general_question,
    ROUTE_RAG,
    ROUTE_LLM,
    ROUTE_REJECT,
)
from app.services.retriever import query_document
from app.database import get_db
from app.models import Message, Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    collection_name: str
    chat_history: list[tuple[str, str]] = []


REJECT_MESSAGE = (
    "I'm a document assistant — I can only help with questions about "
    "your uploaded documents or general knowledge questions. "
    "I can't help with that request."
)


@router.post("/")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    try:
        route = route_query(request.question)
        logger.info("Query routed", extra={"route": route})

        if route == ROUTE_REJECT:
            answer = REJECT_MESSAGE
            sources = []

        elif route == ROUTE_LLM:
            answer = answer_general_question(
                question=request.question, chat_history=request.chat_history
            )
            sources = []

        else:
            result = query_document(
                question=request.question,
                collection_name=request.collection_name,
                chat_history=request.chat_history,
            )
            answer = result["answer"]
            sources = result["sources"]

        # Find the document record
        doc_result = await db.execute(
            select(Document).where(Document.collection_name == request.collection_name)
        )
        document = doc_result.scalar_one_or_none()

        # Save both the user message and assistant response to PostgreSQL
        if document:
            user_msg = Message(
                document_id=document.id,
                role="user",
                content=request.question,
            )
            assistant_msg = Message(
                document_id=document.id,
                role="assistant",
                content=answer,
                route=route,
                sources=sources,
            )
            db.add(user_msg)
            db.add(assistant_msg)

        return {"answer": answer, "sources": sources, "route": route}

    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")
