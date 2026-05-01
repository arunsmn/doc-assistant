import os
import pdfplumber
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from app.config import settings


def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"}
    )


def get_vector_store(collection_name: str):
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


def extract_text_from_pdf(file_path: str) -> list[Document]:
    """
    Uses pdfplumber instead of PyPDFLoader.

    The key difference: pdfplumber understands table structure.
    For each page it:
      1. Extracts tables and converts them to readable key: value text
      2. Extracts remaining plain text
      3. Combines both so nothing is lost

    This means "Personal Detail | John Smith" becomes
    "Personal Detail: John Smith" in the chunk — retrievable and readable.
    """
    documents = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_text_parts = []

            # ── Extract tables first ──────────────────────────────────────
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    # Filter out None/empty cells
                    clean_row = [
                        str(cell).strip() for cell in row if cell and str(cell).strip()
                    ]
                    if clean_row:
                        # Convert table row to readable text
                        # ["Name", "John Smith"] → "Name: John Smith"
                        # This format is natural language — LLMs understand it well
                        page_text_parts.append(": ".join(clean_row))

            # ── Extract plain text (non-table content) ────────────────────
            # extract_text() returns text with tables already removed
            # so we get both without duplication
            plain_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if plain_text:
                page_text_parts.append(plain_text.strip())

            # Combine everything from this page
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
    # Step 1: Extract — now with proper table support
    pages = extract_text_from_pdf(file_path)

    if not pages:
        raise ValueError(
            "No text could be extracted. The PDF may be scanned or image-based."
        )

    # Step 2: Chunk
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        add_start_index=True,
    )
    chunks = splitter.split_documents(pages)

    # Step 3: Embed and store
    vector_store = get_vector_store(collection_name)
    vector_store.add_documents(chunks)

    return {
        "pages_loaded": len(pages),
        "chunks_created": len(chunks),
        "collection": collection_name,
    }
