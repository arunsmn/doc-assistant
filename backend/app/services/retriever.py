import time
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.ingestion import get_vector_store
from app.config import settings


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.3,
    )


def format_chat_history(chat_history: list[tuple[str, str]]) -> list:
    messages = []
    for human, assistant in chat_history:
        messages.append(HumanMessage(content=human))
        messages.append(AIMessage(content=assistant))
    return messages


def build_chain(retriever, has_history: bool):
    """
    When there's no chat history, skip the rephrase step entirely.
    The rephrase step only helps with follow-up questions like
    "tell me more about that" — it adds no value on the first question
    and can confuse the LLM when there's nothing to rephrase from.
    """
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
        # No history — use the retriever as-is, no rephrasing needed
        active_retriever = retriever

    # Looser prompt — allows synthesis across chunks, not just direct matching
    # The key change: "based on" instead of "ONLY" — allows the LLM to
    # reason across multiple chunks to answer summary questions
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
                    "- If the document clearly answers the question → give a direct, well-structured answer\n"
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
    vector_store = get_vector_store(collection_name)
    retriever = vector_store.as_retriever(search_kwargs={"k": settings.top_k})

    # Pass whether we have history so build_chain can decide
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
                print(f"Rate limited. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise e

    # Extract and deduplicate sources
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
