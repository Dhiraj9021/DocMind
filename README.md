# DocMind

A document Q&A tool. Upload a PDF, ask questions, get answers with page citations.

Built every component written from scratch to understand what's actually happening.

---

## What it does

- Upload one or more PDFs
- Ask questions in plain English
- Get answers pulled directly from the document, with source and page number
- Switch between single-document mode and cross-document search

---

## Stack

| Part | Technology |
|---|---|
| Backend | FastAPI |
| Vector database | ChromaDB |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| LLM | LLaMA3 via Groq API |
| PDF parsing | PyPDF |
| Frontend | React |

Embeddings run locally — no OpenAI API needed for search.

---

## How it works

```
PDF upload
  → extract text page by page
  → split into 500-char chunks with 50-char overlap
  → embed each chunk (384-dimensional vector)
  → store in ChromaDB with source + page metadata

User asks a question
  → embed the question with the same model
  → find top-5 most similar chunks in ChromaDB
  → filter out anything below 0.15 similarity (prevents hallucination)
  → send chunks as context to LLaMA3
  → return answer with citations
```

---

## Project structure

```
DocMind/
├── backend/
│   ├── main.py        # API endpoints
│   ├── ingest.py      # PDF → chunks → ChromaDB
│   ├── embedder.py    # sentence-transformer wrapper
│   ├── retriever.py   # semantic search with document filter
│   ├── generator.py   # LLaMA3 answer generation
│   └── config.py      # settings
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── components/
├── data/uploads/      # uploaded PDFs
└── vectorstore/       # ChromaDB storage
```

---

## Running locally

**Requirements:** Python 3.11+, Node 18+, free Groq API key

```bash
# Clone
git clone https://github.com/yourusername/paperbrain
cd DocMind

# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Add your Groq key to backend/.env
echo "GROQ_API_KEY=your_key_here" > .env

python main.py
# Runs on http://localhost:8000
```

```bash
# Frontend (new terminal)
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

Get a free Groq key at console.groq.com

---

## API

```
POST /upload              upload a PDF
POST /query               ask a question
DELETE /document/{name}   remove a document
GET  /health              status check
```

Query example:
```json
{
  "question": "What is the notice period?",
  "document_name": "contract.pdf"
}
```

Response:
```json
{
  "answer": "The notice period is 30 days [Source: contract.pdf, Page 3]",
  "sources": [{ "file": "contract.pdf", "page": "3", "similarity": 0.84 }],
  "chunks_used": 4
}
```

---

## Design decisions

**No LangChain** — wanted to understand each step. Chunking, embedding, retrieval, and generation are all explicit. Easier to debug and explain.

**Local embeddings** — all-MiniLM-L6-v2 runs on CPU, costs nothing, and works well for English text. The embedding model can be swapped in config.py.

**0.15 similarity threshold** — resume and contract text is short and terse, which produces lower similarity scores than paragraphs. Tested real matches at 29–49%; anything under 0.15 is typically noise.

**Document isolation** — each query passes a `document_name` filter to ChromaDB so answers never bleed across documents.

---
