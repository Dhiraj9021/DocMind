# backend/ingest.py

import os
import re
import uuid
from pypdf import PdfReader
import chromadb
from embedder import embed_batch
from config import (
    VECTORSTORE_PATH, COLLECTION_NAME,
    CHUNK_SIZE, CHUNK_OVERLAP
)


# ─────────────────────────────────────────────────────────────────────
# STEP A: LOAD PDF
# ─────────────────────────────────────────────────────────────────────

def load_pdf(file_path: str) -> str:
    """
    Extract all text from a PDF, page by page.

    WHAT: PDF file → one big string of text
    WHY:  We need raw text before we can chunk or embed it
    HOW:  PyPDF reads each page and extracts text layer

    Why PyPDF and not other libraries?
    - pdfplumber: better for tables, slower, more complex
    - PyMuPDF (fitz): fastest, but has licensing restrictions
    - pypdf: pure Python, simple, handles 90% of PDFs, free
    For most resumes/reports/docs → pypdf is perfect.
    For PDFs with complex tables → switch to pdfplumber.

    Why add [PAGE X] markers?
    So when we chunk later, we know which page each chunk
    came from → enables "Source: resume.pdf, Page 2" citations.
    """
    reader = PdfReader(file_path)

    full_text = ""
    total_pages = len(reader.pages)
    print(f"   📖 Found {total_pages} page(s)")

    for page_num, page in enumerate(reader.pages):
        page_text = page.extract_text()

        if page_text and page_text.strip():
            # Add page marker — used later for citation metadata
            full_text += f"\n[PAGE {page_num + 1}]\n{page_text}"
        else:
            # This page is probably a scanned image
            # PyPDF can't extract text from images
            # Solution (advanced): add OCR with pytesseract
            print(f"   ⚠️  Page {page_num + 1} has no extractable text "
                  f"(might be a scanned image)")

    return full_text


# ─────────────────────────────────────────────────────────────────────
# STEP B: CLEAN TEXT
# ─────────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """
    Remove noise from PDF-extracted text.

    WHAT: messy text → clean text
    WHY:  dirty text produces worse embeddings
          garbage in → garbage vectors → bad search results
    HOW:  regex patterns to fix common PDF extraction issues

    Common PDF extraction problems:
    1. Multiple blank lines (PDFs use whitespace for layout)
    2. Multiple spaces (PDF columns sometimes merge weirdly)
    3. Non-ASCII characters (bullet points become â€¢ etc.)
    4. Hyphenated line breaks ("impor-\ntant" instead of "important")
    """

    # Fix hyphenated line breaks
    # PDFs sometimes break long words across lines with a hyphen
    # "impor-\ntant" → "important"
    text = re.sub(r'-\n', '', text)

    # Collapse 3+ newlines into 2
    # Keeps paragraph breaks but removes excessive spacing
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Collapse multiple spaces into one
    text = re.sub(r' {2,}', ' ', text)

    # Remove non-printable characters (keep newlines)
    # \x20-\x7E = printable ASCII range
    text = re.sub(r'[^\x20-\x7E\n]', ' ', text)

    # Final strip
    return text.strip()


# ─────────────────────────────────────────────────────────────────────
# STEP C: CHUNK TEXT
# ─────────────────────────────────────────────────────────────────────

def chunk_text(text: str, source_file: str) -> list[dict]:
    """
    Split text into overlapping chunks with metadata.

    WHAT: big text string → list of chunk dicts
    WHY:  LLMs have context limits. We only send relevant chunks.
    HOW:  sliding window with overlap

    Each chunk dict:
    {
        "text":     "actual content here...",
        "source":   "resume.pdf",
        "page":     "2",
        "chunk_id": 3
    }

    Why sliding window with overlap?

    Text: "...end of topic A. Start of topic B..."
                    ↑ chunk boundary here

    WITHOUT overlap:
    Chunk 4: "...end of topic A."          ← misses "Start of topic B"
    Chunk 5: "Start of topic B..."         ← misses "end of topic A"
    If the answer is "topic A leads into topic B" → missed entirely

    WITH overlap (50 chars):
    Chunk 4: "...end of topic A. Start of"    ← has boundary context
    Chunk 5: "topic A. Start of topic B..."   ← also has boundary context
    Now either chunk can answer boundary questions.
    """

    chunks = []
    chunk_id = 0

    # ── Parse [PAGE X] markers to know which page each section is on ──
    # re.split with capture group () keeps the matched text in results
    # Input:  "[PAGE 1]\ntext1\n[PAGE 2]\ntext2"
    # Output: ['', '1', '\ntext1\n', '2', '\ntext2']
    page_segments = re.split(r'\[PAGE (\d+)\]', text)

    # Rebuild as list of (page_number, page_text) tuples
    page_texts = []
    i = 1
    while i < len(page_segments) - 1:
        page_num  = page_segments[i]       # e.g. "1"
        page_content = page_segments[i + 1]  # e.g. "\nDhiraj Patil..."
        page_texts.append((page_num, page_content))
        i += 2

    # Fallback: if no [PAGE X] markers found, treat all as page 1
    if not page_texts:
        page_texts = [("1", text)]

    # ── Sliding window chunking ────────────────────────────────────────
    for page_num, page_text in page_texts:
        page_text = page_text.strip()
        if not page_text:
            continue

        start = 0
        while start < len(page_text):
            end = start + CHUNK_SIZE

            chunk_content = page_text[start:end]

            # Skip tiny chunks (usually just page headers/footers)
            if len(chunk_content.strip()) > 50:
                chunks.append({
                    "text":     chunk_content.strip(),
                    "source":   os.path.basename(source_file),
                    "page":     page_num,
                    "chunk_id": chunk_id
                })
                chunk_id += 1

            # Move window forward
            # stride = CHUNK_SIZE - CHUNK_OVERLAP
            # e.g. 500 - 50 = 450 chars forward each step
            start += (CHUNK_SIZE - CHUNK_OVERLAP)

    return chunks


# ─────────────────────────────────────────────────────────────────────
# STEP D: STORE IN CHROMADB WITH EMBEDDINGS
# ─────────────────────────────────────────────────────────────────────

def get_chroma_collection():
    """
    Connect to ChromaDB and get (or create) our collection.

    WHAT: returns a ChromaDB collection object
    WHY:  we need the collection to add/query documents
    HOW:  PersistentClient saves data to disk (survives restarts)

    PersistentClient vs EphemeralClient:
    - PersistentClient: saves to disk → data survives app restart ✅
    - EphemeralClient:  in-memory only → data lost on restart ❌
    Always use PersistentClient for real apps.

    get_or_create_collection:
    - If collection exists → returns it (preserves existing data)
    - If not → creates new one
    Safe to call multiple times without data loss.

    hnsw:space = "cosine":
    - Tells ChromaDB to use cosine similarity for search
    - Must match how our embeddings are normalized
    - We normalize embeddings → cosine is correct choice
    """
    client = chromadb.PersistentClient(path=VECTORSTORE_PATH)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    return collection


def store_chunks_with_embeddings(chunks: list[dict]) -> int:
    """
    Embed all chunks then save everything to ChromaDB.

    WHAT: chunk dicts → embedded and stored in ChromaDB
    WHY:  stored embeddings enable fast similarity search later
    HOW:  batch embed first, then batch insert to ChromaDB

    ChromaDB's add() needs 4 parallel lists:
    - ids:        unique ID for each chunk (for deduplication)
    - documents:  the actual text of each chunk
    - embeddings: the vector for each chunk
    - metadatas:  source, page, chunk_id for each chunk

    Why generate UUIDs for IDs?
    - UUIDs are universally unique → no collisions even across
      multiple ingestion runs with different documents
    - Alternative: use hash of text → deterministic but collision risk
    """
    collection = get_chroma_collection()

    # Extract just texts for batch embedding
    texts = [chunk["text"] for chunk in chunks]

    # Embed all at once (much faster than one by one)
    embeddings = embed_batch(texts)

    # Build parallel lists for ChromaDB
    ids         = [str(uuid.uuid4()) for _ in chunks]
    documents   = texts
    metadatas   = [
        {
            "source":   chunk["source"],
            "page":     chunk["page"],
            # ChromaDB metadata values must be strings/int/float
            # chunk_id is int → convert to string to be safe
            "chunk_id": str(chunk["chunk_id"])
        }
        for chunk in chunks
    ]

    # Insert everything in one batch operation
    # Much faster than calling add() for each chunk individually
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(chunks)


# ─────────────────────────────────────────────────────────────────────
# MAIN PIPELINE: PDF → ChromaDB
# ─────────────────────────────────────────────────────────────────────

def ingest_document(file_path: str) -> dict:
    """
    Complete pipeline: PDF file → stored in ChromaDB.

    Orchestrates all 4 steps:
    load_pdf → clean_text → chunk_text → store_chunks_with_embeddings
    """
    print(f"\n{'='*50}")
    print(f"📄 INGESTING: {os.path.basename(file_path)}")
    print(f"{'='*50}")

    # Step 1: Extract
    raw_text = load_pdf(file_path)
    print(f"   ✅ Extracted {len(raw_text):,} characters")

    # Step 2: Clean
    clean = clean_text(raw_text)
    reduction = len(raw_text) - len(clean)
    print(f"   ✅ Cleaned text (removed {reduction} noisy characters)")

    # Step 3: Chunk
    chunks = chunk_text(clean, file_path)
    print(f"   ✅ Created {len(chunks)} chunks "
          f"({CHUNK_SIZE} chars, {CHUNK_OVERLAP} overlap)")

    # Show chunk preview
    for i, chunk in enumerate(chunks[:2], 1):
        preview = chunk['text'][:80].replace('\n', ' ')
        print(f"      Chunk {i} preview: '{preview}...'")

    # Step 4: Embed + Store
    stored = store_chunks_with_embeddings(chunks)

    print(f"\n✅ INGESTION COMPLETE!")
    print(f"   File:   {os.path.basename(file_path)}")
    print(f"   Chunks: {stored} stored in ChromaDB")
    print(f"{'='*50}\n")

    return {
        "file":           os.path.basename(file_path),
        "characters":     len(raw_text),
        "chunks_created": len(chunks),
        "status":         "success"
    }


# ─────────────────────────────────────────────────────────────────────
# TEST: python ingest.py path/to/file.pdf
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ingest.py path/to/file.pdf")
        sys.exit(1)

    result = ingest_document(sys.argv[1])

    # Verify what's stored
    collection = get_chroma_collection()
    total = collection.count()
    print(f"📦 Total chunks in ChromaDB: {total}")

    # Peek at stored data
    sample = collection.peek(1)
    print(f"\n🔍 Sample stored chunk:")
    print(f"   Text:           {sample['documents'][0][:150]}...")
    print(f"   Embedding dims: {len(sample['embeddings'][0])}")
    print(f"   Metadata:       {sample['metadatas'][0]}")