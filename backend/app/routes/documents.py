import os
import uuid
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from app.services.ingestion import ingest_document, get_vector_store
from app.evals.scorer import run_evaluation
from app.database import get_db
from app.models import Document, EvalResult, Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = "./uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),  # DB session injected automatically
):
    # Validate file type
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported right now")

    # Save the uploaded file temporarily
    # uuid prevents name collisions if two people upload "report.pdf"
    file_id = str(uuid.uuid4())
    collection_name = f"doc_{file_id}"
    file_path = f"{UPLOAD_DIR}/{file_id}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run the ingestion pipeline
    try:
        result = ingest_document(file_path, collection_name)
    except Exception as e:
        raise HTTPException(500, f"Ingestion failed: {str(e)}")

    # Save document record to PostgreSQL
    document = Document(
        filename=file.filename,
        collection_name=collection_name,
        pages=result["pages_loaded"],
        chunks=result["chunks_created"],
    )
    db.add(document)
    await db.flush()  # flush to get the generated ID without committing yet

    return {
        "collection_name": collection_name,
        "filename": file.filename,
        "pages_loaded": result["pages_loaded"],
        "chunks_created": result["chunks_created"],
        "message": "Document ready for questions",
    }


@router.get("/")
async def list_documents(db: AsyncSession = Depends(get_db)):
    """Returns all uploaded documents — powers the sidebar on page reload."""
    result = await db.execute(select(Document).order_by(Document.uploaded_at.desc()))
    documents = result.scalars().all()
    return [
        {
            "document_id": str(doc.id),
            "collection_name": doc.collection_name,
            "filename": doc.filename,
            "pages": doc.pages,
            "chunks": doc.chunks,
            "uploaded_at": doc.uploaded_at.isoformat(),
        }
        for doc in documents
    ]


@router.delete("/{collection_name}")
async def delete_document(collection_name: str, db: AsyncSession = Depends(get_db)):
    """Deletes a document, its chat history, and its vector collection."""
    result = await db.execute(
        select(Document).where(Document.collection_name == collection_name)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(404, "Document not found")

    # Remove dependent rows first — no cascade configured at the DB level
    await db.execute(sa_delete(Message).where(Message.document_id == document.id))
    await db.execute(sa_delete(EvalResult).where(EvalResult.document_id == document.id))
    await db.delete(document)

    # Remove the Chroma collection for this document
    try:
        get_vector_store(collection_name).delete_collection()
    except Exception as e:
        logger.warning(f"Failed to delete Chroma collection {collection_name}: {e}")

    return {"message": "Document deleted"}


@router.post("/evaluate/{collection_name}")
async def evaluate(collection_name: str, db: AsyncSession = Depends(get_db)):
    """
    Runs the full evaluation suite against a collection.
    Takes 1-2 minutes depending on number of questions.
    """
    try:
        report = run_evaluation(collection_name)

        # Find the document this collection belongs to
        result = await db.execute(
            select(Document).where(Document.collection_name == collection_name)
        )
        document = result.scalar_one_or_none()

        # Save each eval result to PostgreSQL
        if document:
            for r in report["results"]:
                eval_result = EvalResult(
                    document_id=document.id,
                    question=r["question"],
                    expected_answer=r["expected_answer"],
                    actual_answer=r["actual_answer"],
                    score=r["score"],
                    route_correct=r["route_correct"],
                )
                db.add(eval_result)

        return report
    except Exception as e:
        raise HTTPException(500, f"Evaluation failed: {str(e)}")
