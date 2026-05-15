import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.agents.tools import create_tools

logger = logging.getLogger(__name__)


def get_llm():
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key or ""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.3,
        request_timeout=30,
    )


def run_agent(
    question: str, collection_name: str, chat_history: list[tuple[str, str]] = []
) -> dict:
    """
    Two-phase agent:
    Phase 1 — Tool selection: LLM decides which tools to call
    Phase 2 — Synthesis: LLM combines tool results into final answer

    This is more reliable than a ReAct loop for our use case because:
    - No infinite loop risk
    - Predictable number of LLM calls
    - Still demonstrates multi-tool reasoning
    """
    logger.info("Running agent", extra={"question": question})

    llm = get_llm()
    tools = create_tools(collection_name)

    # Build tool map for easy lookup
    tool_map = {t.name: t for t in tools}

    # ── Phase 1: Tool planning ────────────────────────────────────────────
    # Ask the LLM which tools to call and with what inputs
    planning_prompt = f"""You are a document research assistant. Given a question, 
decide which tools to call to answer it thoroughly.

AVAILABLE TOOLS:
- search_document(query): Search for specific info in the uploaded document
- summarise_document(): Get a broad overview of the document
- extract_key_points(topic): Extract key ideas, optionally filtered by topic
- answer_from_knowledge(question): Answer from general knowledge when document lacks info

QUESTION: {question}

Respond with a JSON array of tool calls in this exact format:
[
  {{"tool": "tool_name", "input": "input_value"}},
  {{"tool": "tool_name", "input": "input_value"}}
]

Rules:
- Include 1-3 tool calls maximum
- For comparison questions → include both search_document AND answer_from_knowledge
- For document-only questions → use search_document or summarise_document
- For key points → use extract_key_points
- Only use answer_from_knowledge when document won't have the answer

Return ONLY the JSON array, nothing else."""

    plan_response = llm.invoke([HumanMessage(content=planning_prompt)])

    # Parse the tool plan
    import json
    import re

    try:
        raw = str(plan_response.content).strip()
        # Extract JSON array from response
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            tool_plan = json.loads(match.group())
        else:
            tool_plan = [{"tool": "search_document", "input": question}]
    except Exception:
        tool_plan = [{"tool": "search_document", "input": question}]

    logger.info("Tool plan", extra={"plan": tool_plan})

    # ── Phase 2: Execute tools ────────────────────────────────────────────
    tool_results = []
    tool_calls_made = []

    for call in tool_plan[:3]:  # max 3 tools
        tool_name = call.get("tool", "search_document")
        tool_input = call.get("input", "")

        if tool_name not in tool_map:
            continue

        logger.info(f"Tool called: {tool_name}", extra={"input": tool_input})

        try:
            result = tool_map[tool_name].invoke(tool_input)
            tool_results.append(f"[{tool_name}]\n{result}")
            tool_calls_made.append({"tool": tool_name, "input": {"query": tool_input}})
        except Exception as e:
            logger.error(f"Tool {tool_name} failed", exc_info=True)
            tool_results.append(f"[{tool_name}]\nError: {str(e)}")

    # ── Phase 3: Synthesise ───────────────────────────────────────────────
    context = "\n\n".join(tool_results)

    synthesis_prompt = f"""You are an expert document research assistant.

Using the information gathered from research tools below, provide a comprehensive 
answer to the user's question.

RESEARCH RESULTS:
{context}

QUESTION: {question}

Instructions:
- For results from search_document/summarise_document/extract_key_points → 
  use that content directly in your answer
- For results marked GENERAL_KNOWLEDGE_NEEDED → 
  answer that part from your own knowledge
- Clearly distinguish between what the document says vs general knowledge
- Synthesise everything into one clear, well-structured answer
"""

    messages = []
    for human, assistant in chat_history:
        messages.append(HumanMessage(content=human))
    messages.append(HumanMessage(content=synthesis_prompt))

    final_response = llm.invoke(messages)

    logger.info(
        "Agent completed",
        extra={
            "tools_used": len(tool_calls_made),
            "tool_names": [t["tool"] for t in tool_calls_made],
        },
    )

    return {
        "answer": final_response.content,
        "tool_calls": tool_calls_made,
        "steps": len(tool_calls_made),
    }
