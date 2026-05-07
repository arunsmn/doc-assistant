import os
import logging
import pdfplumber
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import SecretStr
from app.config import settings

logger = logging.getLogger(__name__)

_embeddings_instance = None


def get_embeddings():
    global _embeddings_instance
    if _embeddings_instance is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        os.environ["GOOGLE_API_KEY"] = settings.google_api_key or ""
        logger.info("Loading Gemini embeddings model")
        _embeddings_instance = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
        )
        logger.info("Gemini embeddings model ready")
    return _embeddings_instance


def get_vector_store(collection_name: str):
    from langchain_community.vectorstores import Chroma

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
    logger.info(
        "Starting ingestion",
        extra={"file": os.path.basename(file_path), "collection": collection_name},
    )

    pages = extract_text_from_pdf(file_path)

    if not pages:
        raise ValueError(
            "No text could be extracted. The PDF may be scanned or image-based."
        )

    logger.info("PDF extracted", extra={"pages": len(pages)})

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(pages)

    logger.info("Text chunked", extra={"chunks": len(chunks)})

    vector_store = get_vector_store(collection_name)
    vector_store.add_documents(chunks)

    logger.info(
        "Ingestion complete",
        extra={
            "pages": len(pages),
            "chunks": len(chunks),
            "collection": collection_name,
        },
    )

    return {
        "pages_loaded": len(pages),
        "chunks_created": len(chunks),
        "collection": collection_name,
    }
