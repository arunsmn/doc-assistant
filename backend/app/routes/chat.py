import logging
import json
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
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
from app.services.retriever import query_document, stream_document_query
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


import asyncio


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    route = route_query(request.question)
    logger.info("Query routed for streaming", extra={"route": route})

    async def generate():
        full_answer = ""
        sources = []

        try:
            if route == ROUTE_REJECT:
                yield f"data: {json.dumps({'type': 'token', 'content': REJECT_MESSAGE})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'route': 'reject'})}\n\n"
                return

            elif route == ROUTE_LLM:
                answer = answer_general_question(
                    question=request.question, chat_history=request.chat_history
                )
                for word in answer.split(" "):
                    chunk = word + " "
                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                    await asyncio.sleep(0)  # yield control to event loop
                yield f"data: {json.dumps({'type': 'done', 'route': 'llm'})}\n\n"

            else:  # RAG
                # Run the synchronous generator in a thread pool
                # so it doesn't block the event loop
                import queue
                import threading

                q = queue.Queue()

                def run_stream():
                    try:
                        for chunk in stream_document_query(
                            question=request.question,
                            collection_name=request.collection_name,
                            chat_history=request.chat_history,
                        ):
                            q.put(chunk)
                    finally:
                        q.put(None)  # sentinel to signal completion

                thread = threading.Thread(target=run_stream)
                thread.start()

                while True:
                    # Check queue without blocking event loop
                    try:
                        chunk = q.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.01)  # small wait, then check again
                        continue

                    if chunk is None:
                        break

                    # Parse for sources and answer tracking
                    try:
                        data = json.loads(chunk.replace("data: ", "").strip())
                        if data["type"] == "sources":
                            sources = data["sources"]
                        elif data["type"] == "token":
                            full_answer += data["content"]
                    except Exception:
                        pass

                    yield chunk

                thread.join()

            # Save to database
            doc_result = await db.execute(
                select(Document).where(
                    Document.collection_name == request.collection_name
                )
            )
            document = doc_result.scalar_one_or_none()

            if document and full_answer:
                db.add(
                    Message(
                        document_id=document.id,
                        role="user",
                        content=request.question,
                    )
                )
                db.add(
                    Message(
                        document_id=document.id,
                        role="assistant",
                        content=full_answer,
                        route=route,
                        sources=sources,
                    )
                )
                await db.commit()

        except Exception as e:
            logger.error("Streaming failed", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "X-Content-Type-Options": "nosniff",
            "Connection": "keep-alive",
        },
    )
