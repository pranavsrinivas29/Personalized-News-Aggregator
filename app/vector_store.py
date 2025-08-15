# app/vector_store.py
from typing import List, Dict, Any, Optional
import uuid
import chromadb
from chromadb.config import Settings
from app.embeddings import embed_text
import config
from pathlib import Path

# ---- schema (metadata keys we store per chunk)
META_USER_ID  = "user_id"
META_TITLE    = "title"
META_LINK     = "link"
META_SNIPPET  = "snippet"
META_CHUNK_IX = "chunk_ix"

# ---- client & collection helpers
Path(config.VECTOR_DB_DIR).mkdir(parents=True, exist_ok=True)

_client = chromadb.PersistentClient(
    path=config.VECTOR_DB_DIR,
    settings=Settings(allow_reset=False)
)

def _collection_name(user_id: int) -> str:
    return f"{config.CHROMA_COLLECTION_PREFIX}{user_id}"

def get_or_create_collection(user_id: int):
    name = _collection_name(user_id)
    try:
        return _client.get_collection(name=name)
    except:
        return _client.create_collection(name=name, metadata={"hnsw:space": "cosine"})

# ---- public API: add chunks and query
def add_article_chunks(
    user_id: int,
    title: str,
    link: str,
    chunks: List[str],
    snippet: str = ""
) -> int:
    """Embed and upsert chunks for a single article. Returns number stored."""
    if not chunks:
        return 0
    col = get_or_create_collection(user_id)

    ids, docs, metas, embs = [], [], [], []
    for j, chunk in enumerate(chunks):
        vec = embed_text(chunk)
        ids.append(str(uuid.uuid4()))
        docs.append(chunk)
        metas.append({
            META_USER_ID: user_id,
            META_TITLE: title,
            META_LINK: link,
            META_SNIPPET: snippet,
            META_CHUNK_IX: j,
        })
        embs.append(vec)

        if len(ids) >= 64:  # batch flush
            col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
            ids, docs, metas, embs = [], [], [], []

    if ids:
        col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
    return len(chunks)

def query(
    user_id: int,
    query_text: str,
    k: int = 8
) -> List[Dict[str, Any]]:
    """Return top-k hits as {text, title, link, snippet} dicts for this user."""
    qvec = embed_text(query_text)
    col  = get_or_create_collection(user_id)
    res  = col.query(query_embeddings=[qvec], n_results=k, where={META_USER_ID: user_id})
    out: List[Dict[str, Any]] = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    for doc, meta in zip(docs, metas):
        meta = meta or {}
        out.append({
            "text":   doc,
            "title":  meta.get(META_TITLE, ""),
            "link":   meta.get(META_LINK, ""),
            "snippet":meta.get(META_SNIPPET, ""),
        })
    return out
