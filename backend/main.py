# backend/main.py

import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ingest import ingest_document
from retriever import retrieve_with_threshold, format_context
from generator import rag_query
from config import UPLOAD_DIR
from typing import Optional

app = FastAPI(
    title="PaperBrain API",
    description="Upload documents, ask questions, get cited answers",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allows index.html opened directly in browser
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── ENDPOINT 1: Health check ──────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "app": "PaperBrain",
        "message": "RAG pipeline is ready"
    }


# ── ENDPOINT 2: Upload PDF ────────────────────────────────────────────

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload PDF → extract → chunk → embed → store in ChromaDB.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files supported. Got: {file.filename}"
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = ingest_document(file_path)
        return {
            "message": f"Successfully ingested {file.filename}",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── ENDPOINT 3: Search only (no LLM) ─────────────────────────────────

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/search")
def search_documents(request: SearchRequest):
    """
    Retrieve relevant chunks without calling LLaMA3.
    Use this to debug retrieval quality independently.
    """
    chunks = retrieve_with_threshold(
        query=request.query,
        top_k=request.top_k
    )

    return {
        "query":             request.query,
        "chunks_found":      len(chunks),
        "results":           chunks,
        "formatted_context": format_context(chunks)
    }


# ── ENDPOINT 4: Full RAG query ────────────────────────────────────────

from typing import Optional

class QueryRequest(BaseModel):
    question: str
    document_name: Optional[str] = None


@app.post("/query")
def query_documents(request: QueryRequest):
    """
    Full RAG pipeline:
    question → retrieve chunks → LLaMA3 → cited answer

    This is the main endpoint the frontend calls.

    Response shape:
    {
        "question":    "What projects did Dhiraj build?",
        "answer":      "Dhiraj built... [Source: Resume.pdf, Page 1]",
        "sources":     [{"file": "Resume.pdf", "page": "1", "similarity": 0.87}],
        "chunks_used": 5,
        "model":       "llama3-8b-8192"
    }
    """
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    try:
        result = rag_query(
    request.question,
    document_name=request.document_name
)
        return {
            "question": request.question,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Run server ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)