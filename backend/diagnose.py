# backend/diagnose.py

import chromadb
from embedder import embed_query
from config import VECTORSTORE_PATH, COLLECTION_NAME

def diagnose(query: str):
    client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)

    print(f"\n{'='*55}")
    print(f" DIAGNOSIS FOR: '{query}'")
    print(f"{'='*55}")
    print(f"Total chunks in DB: {collection.count()}\n")

    query_vector = embed_query(query)

    # Get ALL chunks with their scores (no filtering)
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=collection.count(),
        include=["documents", "metadatas", "distances"]
    )

    print(f"{'Rank':<5} {'Similarity':^12} {'Source':<20} {'Page':<6} Preview")
    print("─" * 80)

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ), 1):
        similarity = round(1 - dist, 4)
        preview = doc[:50].replace('\n', ' ')
        print(f"{i:<5} {similarity*100:>8.1f}%   "
              f"{meta['source']:<20} {meta['page']:<6} {preview}...")

    print("\n─" * 40)
    print("Current threshold: 0.3 (30%)")
    print("Suggested fix: lower to 0.15 for short documents like resumes")

# Test multiple queries
queries = [
    "Python and machine learning",
    "technical skills",
    "projects",
    "Dhiraj education",
    "hackathon"
]

for q in queries:
    diagnose(q)
    print()
