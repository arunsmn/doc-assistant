import os
import pdfplumber
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import SecretStr
from app.config import settings


def get_embeddings():
    """
    Uses Gemini embeddings API instead of local sentence-transformers.
    No model download, no memory overhead — API call instead.
    Free tier: 1500 requests/day which is more than enough for a portfolio project.
    """
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


def extract_text_from_pdf(file_path: str) -> list[Document]:
    documents = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_text_parts = []

            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    clean_row = [
                        str(cell).strip() for cell in row if cell and str(cell).strip()
                    ]
                    if clean_row:
                        page_text_parts.append(": ".join(clean_row))

            plain_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if plain_text:
                page_text_parts.append(plain_text.strip())

            full_text = "\n".join(page_text_parts).strip()

            if full_text:
                documents.append(
                    Document(
                        page_content=full_text,
                        metadata={
                            "page": page_num,
                            "source_file": os.path.basename(file_path),
                        },
                    )
                )

    return documents


def ingest_document(file_path: str, collection_name: str) -> dict:
    pages = extract_text_from_pdf(file_path)

    if not pages:
        raise ValueError(
            "No text could be extracted. The PDF may be scanned or image-based."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(pages)

    vector_store = get_vector_store(collection_name)
    vector_store.add_documents(chunks)

    return {
        "pages_loaded": len(pages),
        "chunks_created": len(chunks),
        "collection": collection_name,
    }
