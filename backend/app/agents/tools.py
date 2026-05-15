import os
import logging
from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from pydantic import SecretStr
from app.config import settings

logger = logging.getLogger(__name__)


def get_embeddings():
    assert settings.google_api_key, "GOOGLE_API_KEY is required"
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=SecretStr(settings.google_api_key),
    )


def get_vector_store(collection_name: str):
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


def create_tools(collection_name: str):
    """
    Creates tool instances bound to a specific document collection.
    """

    @tool
    def search_document(query: str) -> str:
        """
        Searches the uploaded document for information relevant to the query.
        Use this when the question is about specific content in the document.
        Returns the most relevant text chunks found.
        """
        logger.info("Tool called: search_document", extra={"query": query})
        try:
            vector_store = get_vector_store(collection_name)
            docs = vector_store.similarity_search(query, k=settings.top_k)
            if not docs:
                return "No relevant content found in the document for this query."
            results = []
            for i, doc in enumerate(docs, 1):
                page = doc.metadata.get("page", "unknown")
                results.append(f"[Chunk {i} — Page {page}]\n{doc.page_content}")
            return "\n\n".join(results)
        except Exception as e:
            logger.error("search_document failed", exc_info=True)
            return f"Search failed: {str(e)}"

    @tool
    def summarise_document(placeholder: str = "") -> str:
        """
        Generates a comprehensive summary of the entire document.
        Use this when asked to summarise or give an overview of the document.
        The placeholder argument is not used — call with an empty string.
        """
        logger.info("Tool called: summarise_document")
        try:
            vector_store = get_vector_store(collection_name)
            docs = vector_store.similarity_search(
                "main topics overview summary introduction conclusion", k=10
            )
            if not docs:
                return "Could not retrieve document content for summarisation."
            context = "\n\n".join(doc.page_content for doc in docs)
            return f"Document content for summarisation:\n\n{context}"
        except Exception as e:
            logger.error("summarise_document failed", exc_info=True)
            return f"Summarisation failed: {str(e)}"

    @tool
    def extract_key_points(topic: str = "") -> str:
        """
        Extracts the key points from the document, optionally filtered by topic.
        Use this when asked for key points, main ideas, or important takeaways.
        Pass a topic to focus on specific areas, or empty string for overall key points.
        """
        logger.info("Tool called: extract_key_points", extra={"topic": topic})
        try:
            vector_store = get_vector_store(collection_name)
            query = topic if topic else "key points main ideas important concepts"
            docs = vector_store.similarity_search(query, k=8)
            if not docs:
                return "Could not find key points in the document."
            context = "\n\n".join(doc.page_content for doc in docs)
            return f"Document content for key point extraction:\n\n{context}"
        except Exception as e:
            logger.error("extract_key_points failed", exc_info=True)
            return f"Key point extraction failed: {str(e)}"

    @tool
    def answer_from_knowledge(question: str) -> str:
        """
        Signals that this question requires general knowledge not found in the document.
        Use this when the document does not contain the relevant information.
        The question will be answered from general knowledge during synthesis.
        """

        logger.info("Tool called: answer_from_knowledge", extra={"question": question})
        # Return the question as a signal — synthesis phase handles the actual answer
        return f"GENERAL_KNOWLEDGE_NEEDED: {question}"

    return [
        search_document,
        summarise_document,
        extract_key_points,
        answer_from_knowledge,
    ]
