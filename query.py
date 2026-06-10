"""
Retrieval + generation pipeline.

Exports:
    ask(question) -> {"answer": str, "sources": list[str]}

Sources are built programmatically from chunk metadata — the LLM never
decides what to cite. Grounding is enforced via the system prompt: the
model is told to refuse rather than guess when context is insufficient.
"""

import os
from groq import Groq
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()

COLLECTION_NAME = "austin_restaurants"
DB_PATH = "chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama-3.3-70b-versatile"
TOP_K = 3

# ── Grounding system prompt ────────────────────────────────────────────────
# "only" and "must" are load-bearing words here; "you should" would be weak.
# The fallback phrase is exact so the UI can detect it if needed.
SYSTEM_PROMPT = """\
You are a helpful guide to Austin restaurants.

RULES — you must follow these exactly:
1. Answer ONLY using information that appears in the context documents below.
2. Do NOT draw on your training data, general knowledge, or outside information.
3. If the context does not contain enough information to answer the question,
   respond with exactly: "I don't have enough information on that."
4. Never guess, estimate, or infer beyond what the documents explicitly state.
5. Keep your answer concise (2–4 sentences unless the question requires more).
"""


# ── ChromaDB client ────────────────────────────────────────────────────────

def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_collection(COLLECTION_NAME, embedding_function=ef)


# ── Retrieval ──────────────────────────────────────────────────────────────

def retrieve(question: str, top_k: int = TOP_K) -> tuple[list[str], list[dict]]:
    collection = _get_collection()
    results = collection.query(query_texts=[question], n_results=top_k)
    return results["documents"][0], results["metadatas"][0]


# ── Source label builder ───────────────────────────────────────────────────
# Constructed here, never delegated to the LLM.

def _format_source(meta: dict) -> str:
    parts = []
    if meta.get("restaurant"):
        parts.append(meta["restaurant"])
    if meta.get("site"):
        parts.append(f"via {meta['site']}")
    elif meta.get("source_type"):
        parts.append(meta["source_type"])
    if meta.get("source_file"):
        parts.append(f"({meta['source_file']})")
    return " ".join(parts) if parts else meta.get("source_file", "unknown")


# ── Generation ─────────────────────────────────────────────────────────────

def ask(question: str) -> dict[str, object]:
    """
    Returns {"answer": str, "sources": list[str], "chunks": list[str]}
    """
    chunks, metadatas = retrieve(question)

    context = "\n\n".join(
        f"[Document {i + 1}]\n{chunk}" for i, chunk in enumerate(chunks)
    )

    user_message = f"Context documents:\n{context}\n\nQuestion: {question}"

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.1,   # low temperature → factual, less creative deviation
        max_tokens=512,
    )

    answer = response.choices[0].message.content.strip()

    # Attribution: built from metadata, never from LLM output
    raw_sources = [_format_source(m) for m in metadatas]
    seen: set[str] = set()
    sources = [s for s in raw_sources if not (s in seen or seen.add(s))]  # type: ignore[func-returns-value]

    return {"answer": answer, "sources": sources, "chunks": chunks}


# ── Quick CLI test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_questions = [
        "Where in Austin can I get Egyptian-inspired BBQ?",
        "Is Loro worth it?",
        "What is the best steakhouse in Austin?",
        "What is the weather like in Austin?",   # out-of-scope — should refuse
    ]

    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {q}")
        result = ask(q)
        print(f"A: {result['answer']}")
        print("Sources:")
        for s in result["sources"]:
            print(f"  • {s}")
