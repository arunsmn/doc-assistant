import os
import re
import logging
from datetime import date
from typing import List, Tuple, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from pydantic import SecretStr
from app.config import settings

logger = logging.getLogger(__name__)

# The three decisions the router can make
ROUTE_RAG = "rag"
ROUTE_LLM = "llm"
ROUTE_REJECT = "reject"


def get_llm():
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key or ""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0,
    )


# This is the prompt that turns Gemini into a router.
# Notice how explicit and constrained it is — we don't want creativity here,
# we want a reliable classifier that always returns one of three words.
ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a query router for a document question-answering system.
Classify the question into exactly one of three categories:

1. "rag" - The question asks about the CONTENT of the uploaded document.
   Use this when the question references the document explicitly OR asks about
   topics that are likely covered in the uploaded document.
   Examples: "What does the document say about X?", "Summarise the document",
             "What are the key points?", "Does the document mention X?"

2. "llm" - The question is clearly general knowledge UNRELATED to any document.
   Use this ONLY when the question has no plausible connection to an uploaded document.
   Examples: "What is the capital of France?", "What is Python?",
             "Who invented the telephone?", "What is machine learning?"

3. "reject" - Harmful, offensive, or completely nonsensical requests.
   Examples: "How do I hack a website?", gibberish text.

KEY RULE: If the question asks WHAT IS X or EXPLAIN X for a well-known concept
that is unlikely to be in a document → choose "llm".
If the question asks WHAT DOES THE DOCUMENT SAY or references document content → choose "rag".

Respond with ONLY one word: rag, llm, or reject.""",
        ),
        ("human", "{question}"),
    ]
)


def route_query(question: str) -> str:
    """
    Classifies a question and returns one of: 'rag', 'llm', 'reject'

    We use temperature=0 so this decision is deterministic —
    the same question always gets the same route.
    """
    llm = get_llm()
    chain = ROUTER_PROMPT | llm

    try:
        response = chain.invoke({"question": question})
    except Exception as e:
        logger.error("Router failed, defaulting to rag", exc_info=True)
        return ROUTE_RAG  # safest fallback

    # Normalize safely
    raw = str(response.content).strip().lower()
    raw = re.sub(r"[^\w\s]", "", raw)  # remove punctuation

    # Take first token only (handles "rag\nexplanation")
    decision = raw.split()[0] if raw else ""

    # Safety net — if Gemini returns something unexpected, default to RAG
    # Better to try retrieval than to wrongly reject a valid question
    if decision not in {ROUTE_RAG, ROUTE_LLM, ROUTE_REJECT}:
        logger.warning(
            "Unexpected router response, defaulting to rag",
            extra={"response": decision},
        )
        return ROUTE_RAG

    logger.info("Query routed", extra={"route": decision})
    return decision


def answer_general_question(
    question: str,
    chat_history: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """
    Used when the router decides ROUTE_LLM.
    Answers directly from Gemini's training knowledge — no document retrieval.
    """
    if chat_history is None:
        chat_history = []

    llm = get_llm()

    # Inject today's date so Gemini knows when "now" is
    today = date.today().strftime("%B %d, %Y")
    messages: List[BaseMessage] = [
        SystemMessage(
            content=(
                f"You are a helpful assistant. "
                f"Today's date is {today}. "
                f"Use this when answering any time-sensitive questions."
            )
        )
    ]

    for human, assistant in chat_history:
        messages.append(HumanMessage(content=human))
        messages.append(AIMessage(content=assistant))

    messages.append(HumanMessage(content=question))

    try:
        response = llm.invoke(messages)
        return str(response.content)
    except Exception as e:
        logger.error("LLM answer failed", exc_info=True)
        return "Sorry, something went wrong while generating the response."
