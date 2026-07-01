# backend/config.py

import os
from dotenv import load_dotenv

# load_dotenv() reads your .env file and puts values
# into environment variables so os.getenv() can find them.
# Without this line, GROQ_API_KEY would be None.
load_dotenv()

# ── LLM Settings ──────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# We read from .env not hardcode because:
# 1. You might push code to GitHub — never expose API keys
# 2. Different environments (dev/prod) use different keys
# 3. One place to change it

LLM_MODEL = "llama-3.1-8b-instant"
# Why llama-3.3-70b-versatile?
#   - 70b = 70 billion parameters (very smart for Q&A)
#   - 8192 = context window size in tokens
#   - Free on Groq
#   - Fast — Groq uses custom hardware (LPUs) not GPUs
# Alternative: "llama3-70b-8192" — smarter but slower

# ── Embedding Settings ────────────────────────────────────────────────

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
# Why this model?
#   - Runs 100% locally on your CPU — zero cost forever
#   - "MiniLM" = Mini Language Model — small but very capable
#   - "L6" = 6 transformer layers
#   - "v2" = version 2 (improved over v1)
#   - 384 dimensions — good balance of quality vs speed
#   - Downloaded once (~90MB), cached forever

EMBEDDING_DIM = 384
# How many numbers represent each chunk.
# OpenAI uses 1536 — more expressive but costs money.
# 384 is enough for our use case.

# ── Chunking Settings ─────────────────────────────────────────────────

CHUNK_SIZE = 500
# Characters per chunk.
# Too small (< 200): each chunk lacks context, poor answers
# Too large (> 1000): chunks too broad, retrieval less precise
# 500 chars ≈ 3-4 sentences — sweet spot for most documents

CHUNK_OVERLAP = 50
# How many characters the next chunk "backs up" into the previous.
# Prevents information loss at chunk boundaries.
# 50 chars ≈ half a sentence of overlap

# ── Retrieval Settings ────────────────────────────────────────────────

TOP_K = 5
# How many chunks to retrieve per query.
# Too few (1-2): might miss the answer
# Too many (10+): too much text for LLM, slower, expensive
# 5 is the standard starting point in production RAG

# ── File Paths ────────────────────────────────────────────────────────

VECTORSTORE_PATH = "../vectorstore"
# Where ChromaDB saves its data on disk.
# Relative path from backend/ folder.
MIN_SIMILARITY = 0.15
UPLOAD_DIR = "../data/uploads"
# Where uploaded PDFs are saved.

# ── ChromaDB Settings ─────────────────────────────────────────────────

COLLECTION_NAME = "rag_documents"
# A collection is like a table in SQL.
# All chunks from all documents go into this one collection.
# In advanced systems you might have one collection per user.