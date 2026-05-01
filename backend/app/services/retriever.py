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
        convert_system_message_to_human=True,
    )


def format_chat_history(chat_history: list[tuple[str, str]]) -> list:
    """
    Converts our API's tuple format into LangChain message objects.

    Our API receives:  [("what is X?", "X is ..."), ("tell me more", "...")]
    LangChain needs:   [HumanMessage("what is X?"), AIMessage("X is ..."), ...]

    We keep tuples in the API because they're simpler to send over JSON.
    We convert here, at the boundary, right before LangChain needs them.
    """
    messages = []
    for human, assistant in chat_history:
        messages.append(HumanMessage(content=human))
        messages.append(AIMessage(content=assistant))
    return messages


def build_chain(retriever):
    """
    Builds the two-step conversational RAG chain.
    Separated into its own function so it's easy to test and reason about.
    """
    llm = get_llm()

    # ── Step 1: History-aware retriever ──────────────────────────────────────
    # Problem this solves: if the user asks "what about its pricing?" as a
    # follow-up, the retriever has no idea what "it" refers to.
    # This prompt tells the LLM to rewrite the question using chat history
    # into a standalone question before hitting Chroma.
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

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, rephrase_prompt
    )

    # ── Step 2: Answer generation ─────────────────────────────────────────────
    # Takes the retrieved chunks and generates a grounded answer.
    # "grounded" means: only answer from the provided context, don't hallucinate.
    answer_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a helpful document assistant. "
                    "Answer the user's question using ONLY the context below. "
                    "If the answer is not in the context, say "
                    "'I could not find this information in the document.' "
                    "Do not make up information.\n\n"
                    "Context:\n{context}"
                ),
            ),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    # create_stuff_documents_chain "stuffs" all retrieved chunks
    # into the {context} slot in the prompt above
    answer_chain = create_stuff_documents_chain(llm, answer_prompt)

    # Combine both steps into one chain
    return create_retrieval_chain(history_aware_retriever, answer_chain)


def query_document(
    question: str, collection_name: str, chat_history: list[tuple[str, str]] = []
) -> dict:
    """
    Full query pipeline with chat history, source citations, and retry logic.
    """
    vector_store = get_vector_store(collection_name)
    retriever = vector_store.as_retriever(search_kwargs={"k": settings.top_k})
    chain = build_chain(retriever)
    formatted_history = format_chat_history(chat_history)

    # Retry logic for Gemini rate limits (free tier = 429 errors)
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

    # Extract and deduplicate source pages for citations
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
