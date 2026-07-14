# backend/main.py

import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from ingest import ingest_document
from retriever import retrieve_with_threshold, format_context
from generator import rag_query
from config import UPLOAD_DIR, VECTORSTORE_PATH, COLLECTION_NAME
import chromadb

app = FastAPI(title="PaperBrain API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "app": "PaperBrain", "message": "RAG pipeline is ready"}


def delete_chunks_for_file(filename: str):
    """Delete all ChromaDB chunks for a given filename."""
    try:
        client     = chromadb.PersistentClient(path=VECTORSTORE_PATH)
        collection = client.get_collection(name=COLLECTION_NAME)
        existing   = collection.get(where={"source": filename})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"Deleted {len(existing['ids'])} chunks for: {filename}")
    except Exception as e:
        print(f"Nothing to delete for {filename}: {e}")


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        delete_chunks_for_file(file.filename)  # remove stale data first
        result = ingest_document(file_path)
        return {
            "message": f"Successfully ingested {file.filename}",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/document/{filename}")
def delete_document(filename: str):
    """
    Delete a document:
    1. Remove all its chunks from ChromaDB
    2. Delete the PDF file from disk
    """
    # 1. Remove from ChromaDB
    delete_chunks_for_file(filename)

    # 2. Remove PDF from disk
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted file from disk: {filename}")

    return {"message": f"{filename} deleted successfully"}


class QueryRequest(BaseModel):
    question: str
    document_name: Optional[str] = None


@app.post("/query")
def query_documents(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    print(f"\nQUERY: {request.question}")
    print(f"FILTER: {request.document_name or 'ALL documents'}")

    try:
        result = rag_query(request.question, document_name=request.document_name)
        return {"question": request.question, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)