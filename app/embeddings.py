"""Embedding generation + FAISS index management."""
from __future__ import annotations
import json, pickle, time
from pathlib import Path
from typing import Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL, INDEX_DIR

_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def build_index(chunks: list[dict], pdf_name: str,
                save_pkl: bool = True) -> dict:
    """
    Build a FAISS index from chunks.
    Returns {index_path, pkl_path, num_chunks, embed_dim, build_time}.
    """
    model = _get_model()
    t0 = time.time()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False,
                              normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)          # inner-product (cosine on L2-normed)
    index.add(embeddings)

    stem = Path(pdf_name).stem
    idx_path = INDEX_DIR / f"{stem}.faiss"
    pkl_path = INDEX_DIR / f"{stem}.pkl"

    faiss.write_index(index, str(idx_path))

    meta = {"chunks": chunks, "dim": dim}
    with open(pkl_path, "wb") as f:
        pickle.dump(meta, f)

    build_time = round(time.time() - t0, 2)
    return {
        "index_path": str(idx_path),
        "pkl_path": str(pkl_path),
        "num_chunks": len(chunks),
        "embed_dim": dim,
        "build_time_s": build_time,
    }


def query_index(query: str, pdf_name: str, top_k: int = 5,
                cosine_threshold: float = 0.0) -> list[dict]:
    """
    Retrieve top-k chunks from a FAISS index.
    Optionally apply cosine-similarity threshold for reranking.
    """
    model = _get_model()
    stem = Path(pdf_name).stem
    idx_path = INDEX_DIR / f"{stem}.faiss"
    pkl_path = INDEX_DIR / f"{stem}.pkl"

    if not idx_path.exists() or not pkl_path.exists():
        raise FileNotFoundError(f"Index not found for {pdf_name}")

    index = faiss.read_index(str(idx_path))
    with open(pkl_path, "rb") as f:
        meta = pickle.load(f)

    q_emb = model.encode([query], normalize_embeddings=True).astype("float32")
    scores, ids = index.search(q_emb, min(top_k * 2, index.ntotal))

    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < 0:
            continue
        if score < cosine_threshold:
            continue
        chunk = meta["chunks"][idx].copy()
        chunk["score"] = float(score)
        results.append(chunk)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]
