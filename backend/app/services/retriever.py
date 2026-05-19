import os
import time
import logging
import json
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.ingestion import get_vector_store
from app.config import settings
from typing import Generator

logger = logging.getLogger(__name__)


def get_llm():
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key or ""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.3,
    )


def format_chat_history(chat_history: list[tuple[str, str]]) -> list:
    messages = []
    for human, assistant in chat_history:
        messages.append(HumanMessage(content=human))
        messages.append(AIMessage(content=assistant))
    return messages


def build_chain(retriever, has_history: bool):
    llm = get_llm()

    if has_history:
        rephrase_prompt = ChatPromptTemplate.from_messages(
            [
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
                (
                    "human",
                    (
                        "Given the conversation above, rephrase my latest question "
                        "into a standalone question that contains all necessary context. "
                        "Return only the rephrased question, nothing else."
                    ),
                ),
            ]
        )
        active_retriever = create_history_aware_retriever(
            llm, retriever, rephrase_prompt
        )
    else:
        active_retriever = retriever

    answer_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are an expert document analyst. "
                    "Your job is to answer questions about the uploaded document accurately and helpfully.\n\n"
                    "DOCUMENT CONTEXT (extracted from the uploaded document):\n{context}\n\n"
                    "INSTRUCTIONS:\n"
                    "1. Read the document context carefully\n"
                    "2. Think about what the question is really asking\n"
                    "3. Use the conversation history to understand follow-up questions\n"
                    "4. Answer based ONLY on what the document says\n\n"
                    "RULES:\n"
                    "- If the document does not EXPLICITLY use the exact words or concept asked about → "
                    "say 'The document does not contain information about this.' "
                    "Do not infer, extrapolate, or synthesise from loosely related content.\n"
                    "- If the document partially answers the question → share what you found and clearly state what is missing\n"
                    "- If the document does not answer the question at all → say 'The document does not contain information about this'\n"
                    "- Never make up facts or guess beyond what the document says\n"
                    "- Match your answer length to the question — short questions get short answers\n"
                    "- If listing multiple points, use a numbered list\n"
                    "- If quoting the document directly, use quotation marks\n\n"
                    "Think step by step, then give your answer."
                ),
            ),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    answer_chain = create_stuff_documents_chain(llm, answer_prompt)
    return create_retrieval_chain(active_retriever, answer_chain)


def query_document(
    question: str, collection_name: str, chat_history: list[tuple[str, str]] = []
) -> dict:
    """Standard non-streaming query — used by evaluation and non-streaming chat."""
    vector_store = get_vector_store(collection_name)
    retriever = vector_store.as_retriever(search_kwargs={"k": settings.top_k})

    chain = build_chain(retriever, has_history=len(chat_history) > 0)
    formatted_history = format_chat_history(chat_history)

    for attempt in range(3):
        try:
            result = chain.invoke(
                {"input": question, "chat_history": formatted_history}
            )
            break
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 30 * (attempt + 1)
                logger.warning(
                    "Rate limited by Gemini",
                    extra={"attempt": attempt + 1, "wait_seconds": wait},
                )
                time.sleep(wait)
            else:
                raise e

    sources = []
    seen = set()
    for doc in result.get("context", []):
        page = doc.metadata.get("page", "unknown")
        source_file = doc.metadata.get("source_file", "unknown")
        key = (source_file, page)
        if key not in seen:
            seen.add(key)
            sources.append(
                {
                    "page": page,
                    "source_file": source_file,
                    "snippet": doc.page_content[:200],
                }
            )

    return {"answer": result["answer"], "sources": sources}


def stream_document_query(
    question: str, collection_name: str, chat_history: list[tuple[str, str]] = []
) -> Generator[str, None, None]:
    """
    Streaming version — yields SSE chunks as tokens arrive from Gemini.
    Uses the Gemini SDK directly for streaming to bypass LangChain buffering.
    Uses LangChain only for the retrieval step (vector search + rephrasing).
    """
    from google import genai as google_genai

    vector_store = get_vector_store(collection_name)
    retriever = vector_store.as_retriever(search_kwargs={"k": settings.top_k})
    formatted_history = format_chat_history(chat_history)

    # ── Step 1: Rephrase question if there's chat history ─────────────────
    if len(chat_history) > 0:
        rephrase_llm = get_llm()
        rephrase_prompt = ChatPromptTemplate.from_messages(
            [
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
                (
                    "human",
                    (
                        "Given the conversation above, rephrase my latest question "
                        "into a standalone question. Return only the rephrased question."
                    ),
                ),
            ]
        )
        rephrase_chain = rephrase_prompt | rephrase_llm
        rephrased = rephrase_chain.invoke(
            {"input": question, "chat_history": formatted_history}
        )
        search_query = str(rephrased.content)
    else:
        search_query = question

    # ── Step 2: Retrieve relevant chunks ──────────────────────────────────
    docs = retriever.invoke(search_query)

    # ── Step 3: Extract and send sources immediately ───────────────────────
    sources = []
    seen = set()
    for doc in docs:
        page = doc.metadata.get("page", "unknown")
        source_file = doc.metadata.get("source_file", "unknown")
        key = (source_file, page)
        if key not in seen:
            seen.add(key)
            sources.append(
                {
                    "page": page,
                    "source_file": source_file,
                    "snippet": doc.page_content[:200],
                }
            )

    yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

    # ── Step 4: Build prompt ───────────────────────────────────────────────
    context = "\n\n".join(doc.page_content for doc in docs)

    history_text = ""
    for human, assistant in chat_history:
        history_text += f"User: {human}\nAssistant: {assistant}\n"

    prompt = (
        f"You are an expert document analyst. "
        f"Answer based ONLY on this document context:\n\n{context}\n\n"
        f"CONVERSATION HISTORY:\n{history_text}\n"
        f"RULES:\n"
        f"- If clearly answered → give direct answer\n"
        f"- If partially answered → share what you found and state what's missing\n"
        f"- If not in document → say 'The document does not contain information about this'\n"
        f"- Never make up facts\n"
        f"Think step by step, then give your answer.\n\n"
        f"QUESTION: {question}"
    )

    # ── Step 5: Stream tokens using Gemini SDK directly ────────────────────
    # Bypasses LangChain which buffers the full response before yielding.
    # The Gemini SDK streams tokens as they arrive from the API.
    client = google_genai.Client(api_key=settings.google_api_key or "")

    for chunk in client.models.generate_content_stream(
        model=settings.gemini_model, contents=prompt
    ):
        if chunk.text:
            yield f"data: {json.dumps({'type': 'token', 'content': chunk.text})}\n\n"

    yield f"data: {json.dumps({'type': 'done', 'route': 'rag'})}\n\n"
