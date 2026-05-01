import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = "./uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
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

    return {
        "collection_name": collection_name,
        "filename": file.filename,
        "pages_loaded": result["pages_loaded"],
        "chunks_created": result["chunks_created"],
        "message": "Document ready for questions",
    }
