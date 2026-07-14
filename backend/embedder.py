# backend/embedder.py

from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL

# ─────────────────────────────────────────────────────────────────────
# WHY LOAD MODEL AT MODULE LEVEL (outside any function)?
#
# Option A - Load inside function (BAD):
#   def embed_text(text):
#       model = SentenceTransformer(...)  # loads every call = 3 sec wait
#       return model.encode(text)
#
# Option B - Load at module level (GOOD):
#   model = SentenceTransformer(...)     # loads ONCE when file is imported
#   def embed_text(text):
#       return model.encode(text)        # instant, model already in memory
#
# FastAPI imports this file once when server starts.
# After that every request uses the already-loaded model.
# ─────────────────────────────────────────────────────────────────────

print(f" Loading embedding model '{EMBEDDING_MODEL}'...")
print(f" (First run downloads ~90MB. Cached forever after.)")

_model = SentenceTransformer(EMBEDDING_MODEL)
# Underscore prefix (_model) is Python convention for
# "private to this module — don't import this directly"

print(f"Embedding model ready\n")


# ─────────────────────────────────────────────────────────────────────
# FUNCTION 1: Embed a single text
# ─────────────────────────────────────────────────────────────────────

def embed_text(text: str) -> list[float]:
    """
    Convert one string into a 384-dimensional vector.

    WHAT:  text string → list of 384 floats
    WHY:   so ChromaDB can do mathematical similarity comparison
    HOW:   sentence-transformers runs the MiniLM model locally

    Args:
        text: any string (chunk content or search query)

    Returns:
        list of 384 floats between -1.0 and 1.0
    """

    # Clean the text before embedding
    # Why replace newlines?
    #   "\n" in the middle of text confuses the tokenizer slightly.
    #   "Python\nskills" → "Python skills" → cleaner token boundary
    text = text.replace("\n", " ").strip()

    if not text:
        raise ValueError("Cannot embed empty text — check your chunks")

    embedding = _model.encode(
        text,
        normalize_embeddings=True
        # normalize_embeddings=True:
        #   Scales the vector so its length (magnitude) = 1.0
        #   This is called "unit normalization"
        #   WHY? When all vectors have length 1, cosine similarity
        #   becomes a simple dot product (faster math).
        #   Also ensures fair comparison regardless of text length.
    )

    # embedding is a numpy array → convert to plain Python list
    # Why? ChromaDB expects list[float], not numpy array
    return embedding.tolist()


# ─────────────────────────────────────────────────────────────────────
# FUNCTION 2: Embed many texts at once (batch processing)
# ─────────────────────────────────────────────────────────────────────

def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Convert many strings into vectors efficiently.

    WHAT:  list of strings → list of 384-float vectors
    WHY:   batching is much faster than embedding one by one
    HOW:   sentence-transformers processes multiple texts in parallel

    Difference between looping embed_text() vs embed_batch():

    Loop (slow):
        for text in texts:
            embed_text(text)   # 100 texts × 0.05s = 5 seconds

    Batch (fast):
        embed_batch(texts)     # 100 texts processed together = 0.5s
        (10× faster because model processes them in parallel)
    """

    if not texts:
        return []

    # Clean all texts
    cleaned = [t.replace("\n", " ").strip() for t in texts]

    # Filter out empty strings (can't embed empty text)
    # Keep track of positions so we can put results back in order
    valid_texts = [t for t in cleaned if t]

    if not valid_texts:
        return []

    print(f" Embedding {len(valid_texts)} chunks locally...")

    embeddings = _model.encode(
        valid_texts,
        batch_size=32,
        # batch_size=32:
        #   Process 32 texts at a time internally.
        #   Higher = faster but uses more RAM.
        #   32 is safe for any laptop with 4GB+ RAM.

        normalize_embeddings=True,
        # Same reason as embed_text — unit vectors for cosine similarity

        show_progress_bar=True
        # Shows a progress bar in terminal — helpful for large PDFs
    )

    print(f"  Done! Each vector has {len(embeddings[0])} dimensions")

    # Convert numpy arrays to Python lists
    return [e.tolist() for e in embeddings]


# ─────────────────────────────────────────────────────────────────────
# FUNCTION 3: Embed a user's search query
# ─────────────────────────────────────────────────────────────────────

def embed_query(query: str) -> list[float]:
    """
    Embed a user's search question.

    WHAT:  question string → vector (same 384 dimensions as chunks)
    WHY:   to compare against stored chunk vectors in ChromaDB
    HOW:   identical to embed_text()

    WHY SEPARATE FUNCTION if it does the same thing?
    1. Code readability — instantly clear this is a QUERY not a chunk
    2. Future-proofing — advanced technique called HyDE
       (Hypothetical Document Embeddings) modifies queries before
       embedding. Having a separate function makes this easy to add.
    3. Interview talking point — shows you understand the distinction
       between indexing (chunks) and querying (user input)
    """
    return embed_text(query)


# ─────────────────────────────────────────────────────────────────────
# TEST: Run this file directly to verify embeddings work
# python embedder.py
# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 50)
    print("EMBEDDING TEST")
    print("=" * 50)

    # Test 1: Single embedding
    test_text = "Python machine learning skills"
    vector = embed_text(test_text)

    print(f"\nTest 1 — Single embed:")
    print(f"  Input:      '{test_text}'")
    print(f"  Dimensions: {len(vector)}")
    print(f"  First 5 values: {[round(v, 4) for v in vector[:5]]}")
    print(f"  Min: {min(vector):.4f}, Max: {max(vector):.4f}")

    # Test 2: Similarity between related texts
    import numpy as np

    v1 = embed_text("Python programming skills")
    v2 = embed_text("coding experience in Python")
    v3 = embed_text("cooking pasta recipe")

    # Cosine similarity = dot product of unit vectors
    # (since we normalized, dot product = cosine similarity)
    sim_related = np.dot(v1, v2)
    sim_unrelated = np.dot(v1, v3)

    print(f"\nTest 2 — Similarity check:")
    print(f"  'Python programming' vs 'coding in Python': {sim_related:.4f}")
    print(f"  'Python programming' vs 'cooking pasta':    {sim_unrelated:.4f}")
    print(f"\n   Related texts should score HIGHER than unrelated")
    print(f"  Result: {sim_related:.4f} > {sim_unrelated:.4f} → "
          f"{' CORRECT' if sim_related > sim_unrelated else '❌ WRONG'}")

    # Test 3: Batch embedding
    batch = [
        "machine learning",
        "deep learning",
        "neural networks",
        "banana smoothie recipe"
    ]
    vectors = embed_batch(batch)
    print(f"\nTest 3 — Batch embed:")
    print(f"  Input: {len(batch)} texts")
    print(f"  Output: {len(vectors)} vectors × {len(vectors[0])} dims")
    print(f"   Batch embedding works!")