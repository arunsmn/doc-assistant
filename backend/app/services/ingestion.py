import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.config import settings


def get_embeddings():
    """
    We use sentence-transformers locally — free, no API key needed.
    'all-MiniLM-L6-v2' is small, fast, and good enough for most RAG use cases.
    """
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"}
    )


def get_vector_store(collection_name: str):
    """
    Each document gets its own Chroma collection.
    This means asking about Doc A never pulls chunks from Doc B.
    """
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


def ingest_document(file_path: str, collection_name: str) -> dict:
    """
    Full pipeline: PDF → pages → chunks → embeddings → Chroma
    Returns a summary of what was stored.
    """
    # 1. Load the PDF — PyPDFLoader preserves page numbers for us
    loader = PyPDFLoader(file_path)
    pages = loader.load()  # each page is a Document with page_content + metadata

    # 2. Chunk the pages
    # RecursiveCharacterTextSplitter tries to split on paragraphs first,
    # then sentences, then words — it's smarter than a naive character split
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,  # tracks character position within the page
    )
    chunks = splitter.split_documents(pages)

    # 3. Tag each chunk with the source filename (useful for citations later)
    for chunk in chunks:
        chunk.metadata["source_file"] = os.path.basename(file_path)

    # 4. Embed and store — Chroma handles both steps in one call
    vector_store = get_vector_store(collection_name)
    vector_store.add_documents(chunks)

    return {
        "pages_loaded": len(pages),
        "chunks_created": len(chunks),
        "collection": collection_name,
    }
