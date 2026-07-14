# backend/retriever.py

import chromadb
from embedder import embed_query
from config import VECTORSTORE_PATH, COLLECTION_NAME, TOP_K


def get_collection():
    """Get the ChromaDB collection (read mode)."""
    client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
    # get_collection (not get_or_create) because at search time
    # the collection MUST already exist. If it doesn't →
    # user hasn't uploaded any docs yet → raise clear error.
    return client.get_collection(name=COLLECTION_NAME)


# ─────────────────────────────────────────────────────────────────────
# CORE SEARCH FUNCTION
# ─────────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    top_k: int = TOP_K,
    document_name: str | None = None
) -> list[dict]:
    """
    Find the most semantically similar chunks for a query.

    WHAT: user question → list of relevant chunks with scores
    WHY:  these chunks become the context for GPT/LLaMA to answer
    HOW:
      1. Embed the query → query vector
      2. ChromaDB HNSW search → compare against all stored vectors
      3. Return top_k closest chunks with similarity scores

    The full search flow inside ChromaDB:
      query vector → HNSW graph traversal → approximate nearest
      neighbours → sorted by cosine distance → return top k

    Returns list of dicts:
    [
        {
            "text":       "Python and machine learning...",
            "source":     "resume.pdf",
            "page":       "1",
            "chunk_id":   "4",
            "similarity": 0.87   ← 1.0 = identical, 0.0 = unrelated
        },
        ...
    ]
    """
    try:
        collection = get_collection()
    except Exception:
        print("No collection found. Upload a document first.")
        return []

    if collection.count() == 0:
        print("Collection is empty. Upload a document first.")
        return []

    # Step 1: Embed the user's question
    print(f"   🔍 Embedding query...")
    query_vector = embed_query(query)
    where_filter = None
    if document_name:
       where_filter = {"source": document_name}
       print(f"   📄 Filtering by document: {document_name}")
    # Step 2: Search ChromaDB
    results = collection.query(
        query_embeddings=[query_vector],
        # [query_vector] not query_vector because ChromaDB supports
        # batching multiple queries at once. We send 1, hence the list.

        n_results=min(top_k, collection.count()),
        # min() prevents error when collection has fewer chunks than top_k
        # e.g. collection has 3 chunks but top_k=5 → ask for 3
        where=where_filter,
        include=["documents", "metadatas", "distances"]
        # documents: the chunk text
        # metadatas: source, page, chunk_id
        # distances: cosine DISTANCE (not similarity — we convert below)
        # Note: "embeddings" not included to save memory
    )

    # Step 3: Parse results
    # results structure (for 1 query):
    # {
    #   "documents": [[chunk1_text, chunk2_text, ...]],  ← list of lists
    #   "metadatas": [[chunk1_meta, chunk2_meta, ...]],
    #   "distances": [[0.12, 0.28, ...]]
    # }
    # [0] because we sent 1 query (index 0)

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        # Convert distance → similarity
        # ChromaDB returns DISTANCE with cosine space:
        # distance = 1 - cosine_similarity
        # So: similarity = 1 - distance
        # distance 0.0 → similarity 1.0 (identical)
        # distance 0.5 → similarity 0.5 (somewhat related)
        # distance 1.0 → similarity 0.0 (completely different)
        similarity = round(1 - dist, 4)

        chunks.append({
            "text":       doc,
            "source":     meta.get("source", "unknown"),
            "page":       meta.get("page", "?"),
            "chunk_id":   meta.get("chunk_id", "?"),
            "similarity": similarity
        })

    # Sort highest similarity first (ChromaDB usually returns sorted
    # but we guarantee the order)
    chunks.sort(key=lambda x: x["similarity"], reverse=True)

    return chunks


# ─────────────────────────────────────────────────────────────────────
# FILTERED SEARCH — with quality threshold
# ─────────────────────────────────────────────────────────────────────

def retrieve_with_threshold(
    query: str,
    top_k: int = TOP_K,
    min_similarity: float = 0.15,
    document_name= None
) -> list[dict]:
    """
    Search with a minimum quality filter.

    WHAT: same as retrieve() but removes low-relevance results
    WHY:  prevents hallucination when query doesn't match docs

    The problem without threshold:
      User asks: "What is the weather today?"
      Your docs have: resume, tech reports (no weather info)
      ChromaDB still returns the "least bad" chunks
      These chunks have 0.1 similarity but get sent to LLaMA anyway
      LLaMA tries to answer from irrelevant context → hallucination

    With threshold (0.3):
      Same scenario → all chunks score < 0.3 → filtered out
      Empty list returned → LLaMA says "I don't know" → honest 

    How to choose threshold:
      0.2 = very lenient (returns more, some irrelevant)
      0.3 = balanced (good default)
      0.5 = strict (only highly relevant chunks)
      Start at 0.3, adjust based on your document type.
    """
    chunks = retrieve(
    query=query,
    top_k=top_k,
    document_name=document_name
    )
    filtered = [c for c in chunks if c["similarity"] >= min_similarity]

    removed = len(chunks) - len(filtered)
    if removed > 0:
        print(f"   Filtered out {removed} low-relevance chunks "
              f"(below {min_similarity} threshold)")

    return filtered


# ─────────────────────────────────────────────────────────────────────
# FORMAT CONTEXT — prepare chunks for the LLM prompt
# ─────────────────────────────────────────────────────────────────────

def format_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a structured context block.

    WHAT: list of chunk dicts → formatted string for LLM prompt
    WHY:  LLM needs clear structure to extract information and cite sources
    HOW:  label each chunk with metadata so LLM can reference it

    Why include source/page/relevance in the label?
    - Source: LLM can say "According to resume.pdf..."
    - Page:   LLM can say "...on page 2"
    - Relevance: helps LLM weight more relevant chunks higher

    This formatted string goes directly into the LLM prompt as:
    "Answer using ONLY the context below:\n{format_context(chunks)}"
    """
    if not chunks:
        return "No relevant context found in the uploaded documents."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        label = (
            f"[CONTEXT {i} | "
            f"Source: {chunk['source']} | "
            f"Page: {chunk['page']} | "
            f"Relevance: {chunk['similarity']*100:.0f}%]"
        )
        parts.append(f"{label}\n{chunk['text']}")

    # Join chunks with a separator so LLM sees them as distinct pieces
    return "\n\n" + ("─" * 50) + "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────
# TEST: python retriever.py "your search query here"
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 \
        else "Python programming skills"

    print(f"\n{'='*50}")
    print(f" SEMANTIC SEARCH TEST")
    print(f"{'='*50}")
    print(f"Query: '{query}'\n")

    chunks = retrieve_with_threshold(query)

    if not chunks:
        print("❌ No relevant chunks found above similarity threshold.")
        print("   Try a different query or lower the threshold.")
    else:
        print(f"✅ Found {len(chunks)} relevant chunk(s):\n")
        for i, c in enumerate(chunks, 1):
            print(f"── Result {i} {'─'*35}")
            print(f"   Source:     {c['source']}, Page {c['page']}")
            print(f"   Similarity: {c['similarity']*100:.1f}%")
            print(f"   Preview:    {c['text'][:200].replace(chr(10), ' ')}...")
            print()

    print(f"\n📋 FORMATTED CONTEXT (what LLM will see):")
    print(format_context(chunks[:2]))