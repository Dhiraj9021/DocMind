from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL
from retriever import retrieve_with_threshold, format_context

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are PaperBrain, an intelligent document assistant.

Answer ONLY from the context provided. Never use your own knowledge.
If context is insufficient, say: "I couldn't find enough information in the uploaded document to answer this."
Always cite sources as [Source: filename, Page X].
Be concise and direct."""


def generate_answer(query: str, chunks: list) -> dict:
    if not chunks:
        return {
            "answer": "I couldn't find relevant information in the selected document. Try rephrasing your question or selecting a different document.",
            "sources": [],
            "chunks_used": 0,
            "model": LLM_MODEL
        }

    context = format_context(chunks)

    user_message = f"""Here are relevant sections from the document:

{context}

Based ONLY on the context above, answer:

Question: {query}

Cite sources as [Source: filename, Page X]"""

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ],
        temperature=0.1,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()

    # Deduplicate sources
    sources = []
    seen = set()
    for chunk in chunks:
        key = f"{chunk.get('file', chunk.get('source', ''))}_p{chunk['page']}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "file":       chunk.get("file", chunk.get("source", "unknown")),
                "page":       chunk["page"],
                "similarity": chunk["similarity"]
            })

    return {
        "answer":      answer,
        "sources":     sources,
        "chunks_used": len(chunks),
        "model":       LLM_MODEL
    }


def rag_query(query: str, document_name: str = None) -> dict:
    """Full RAG pipeline. If document_name given, restrict to that doc only."""
    print(f"\n{'='*50}")
    print(f"QUERY: {query}")
    if document_name:
        print(f"DOC FILTER: {document_name}")
    print(f"{'='*50}")

    chunks = retrieve_with_threshold(
        query=query,
        document_name=document_name   # pass filter to retriever
    )

    print(f"Retrieved {len(chunks)} chunks")
    return generate_answer(query, chunks)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is this document about?"
    result = rag_query(q)
    print(f"\nANSWER:\n{result['answer']}")
    print(f"\nSOURCES: {result['sources']}")