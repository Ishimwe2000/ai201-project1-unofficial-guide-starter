"""
Embedding stage: loads all chunks from ingest.py and stores them in ChromaDB.

Run once (or re-run whenever documents change):
    uv run embed.py
"""

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from ingest import load_documents

COLLECTION_NAME = "austin_restaurants"
DB_PATH = "chroma_db"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def build_index(docs_dir: str = "documents") -> chromadb.Collection:
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

    # Wipe and rebuild so re-runs stay consistent
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME, embedding_function=ef)

    print(f"Loading and chunking documents from {docs_dir}/...")
    chunks = load_documents(docs_dir)

    if not chunks:
        print("No chunks found — add documents and re-run.")
        return collection

    documents = [c.text for c in chunks]
    metadatas = [
        {
            **{k: str(v) for k, v in c.metadata.items()},
            "source_type": c.source_type,
            "source_file": c.source_file,
        }
        for c in chunks
    ]
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"\nIndexed {len(chunks)} chunks into {DB_PATH}/{COLLECTION_NAME}")
    print(f"Embedding model: {EMBEDDING_MODEL}")
    return collection


if __name__ == "__main__":
    build_index()
