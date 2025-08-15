# app/embeddings.py
from typing import List
import os
import requests
import config

# ---- Local fallback: FastEmbed (no protobuf) ----
_FASTEMBED_MODEL = None

def _local_embed(text: str) -> List[float]:
    global _FASTEMBED_MODEL
    if _FASTEMBED_MODEL is None:
        # Defaults to a small, high-quality model
        model_name = os.getenv("LOCAL_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
        from fastembed import TextEmbedding
        _FASTEMBED_MODEL = TextEmbedding(model_name=model_name)
    # fastembed returns a generator over np arrays
    vec = next(_FASTEMBED_MODEL.embed([text]))
    return [float(x) for x in vec.tolist()]

def embed_text(text: str) -> List[float]:
    base = config.OLLAMA_BASE_URL.rstrip("/")

    # 1) Try native Ollama embeddings
    try:
        r = requests.post(
            f"{base}/api/embeddings",
            json={"model": config.EMBED_MODEL, "prompt": text},
            timeout=60,
        )
        if r.status_code == 404:
            raise FileNotFoundError("Ollama native /api/embeddings not available")
        r.raise_for_status()
        return r.json()["embedding"]
    except Exception:
        # 2) Try OpenAI-compatible embeddings
        try:
            r2 = requests.post(
                f"{base}/v1/embeddings",
                json={"model": config.EMBED_MODEL, "input": text},
                timeout=60,
            )
            if r2.status_code == 404:
                # 3) Local fastembed fallback
                return _local_embed(text)
            r2.raise_for_status()
            data = r2.json()
            return data["data"][0]["embedding"]
        except Exception:
            # Last resort: local fastembed
            return _local_embed(text)
