import os
import logging
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from app.config import settings
from app.agents.tools import create_tools

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """You are an expert document research assistant with access to powerful tools.

Your job is to answer questions about uploaded documents accurately and helpfully.

AVAILABLE TOOLS:
- search_document: Search for specific information in the document
- summarise_document: Get a comprehensive overview of the document  
- extract_key_points: Pull out the main ideas and key takeaways

GUIDELINES:
- Always use tools to ground your answers in the document
- For specific questions → use search_document
- For overview requests → use summarise_document
- For key ideas → use extract_key_points
- You can call multiple tools if needed — combine results for a better answer
- After getting tool results, synthesise them into a clear, well-structured answer
- If the document doesn't contain the requested information, say so clearly
- Never make up information not found in the document or tool results
"""


def get_llm():
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key or ""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=0.3,
    )


def run_agent(
    question: str, collection_name: str, chat_history: list[tuple[str, str]] = []
) -> dict:
    """
    Runs the LangGraph ReAct agent on a question.

    ReAct = Reasoning + Acting
    The agent reasons about what tools to use, uses them,
    observes results, reasons again, and repeats until done.

    Returns the final answer and a trace of all tool calls made.
    """
    logger.info("Running LangGraph agent", extra={"question": question})

    llm = get_llm()
    tools = create_tools(collection_name)

    # create_react_agent builds the full LangGraph graph automatically:
    # START → agent node → tools node → agent node → ... → END
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=AGENT_SYSTEM_PROMPT,
    )

    # Build message history
    messages = []
    for human, assistant in chat_history:
        messages.append(HumanMessage(content=human))
        messages.append(AIMessage(content=assistant))
    messages.append(HumanMessage(content=question))

    # Run the agent
    result = agent.invoke({"messages": messages})

    # Extract the final answer (last AIMessage)
    final_answer = ""
    tool_calls_made = []

    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_made.append({"tool": tc["name"], "input": tc["args"]})
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            final_answer = msg.content

    logger.info(
        "Agent completed",
        extra={
            "tools_used": len(tool_calls_made),
            "tool_names": [t["tool"] for t in tool_calls_made],
        },
    )

    return {
        "answer": final_answer,
        "tool_calls": tool_calls_made,
        "steps": len(tool_calls_made),
    }
