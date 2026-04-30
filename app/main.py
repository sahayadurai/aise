"""FastAPI application — RAG Benchmark PDF Data Extractor."""
from __future__ import annotations
import json, uuid, shutil, time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    UPLOAD_DIR, INDEX_DIR, RESULTS_DIR, CHAT_DIR,
    AVAILABLE_MODELS, HOST, PORT, OPENROUTER_API_KEY,
)
from app.pdf_processor import (
    extract_text_chunks, extract_images, extract_tables, extract_ground_truth,
)
from app.embeddings import build_index, query_index
from app.llm_client import chat_completion
from app.benchmarks import run_full_benchmark

app = FastAPI(title="RAG Benchmark PDF Data Extractor", version="1.0.0")

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# ── State ───────────────────────────────────────────────────────────────────

_sessions: dict[str, dict] = {}   # session_id -> session data


def _get_or_create_session(session_id: Optional[str] = None) -> tuple[str, dict]:
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]
    sid = session_id or str(uuid.uuid4())[:8]
    _sessions[sid] = {
        "id": sid,
        "files": [],
        "indices": {},
        "chats": [],
        "ground_truths": {},
        "benchmarks": [],
        "created": datetime.now().isoformat(),
    }
    return sid, _sessions[sid]


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "models": AVAILABLE_MODELS,
    })


@app.get("/api/models")
async def list_models():
    return {"models": AVAILABLE_MODELS}


@app.get("/api/sessions")
async def list_sessions():
    return {"sessions": [
        {"id": s["id"], "files": len(s["files"]),
         "chats": len(s["chats"]), "created": s["created"]}
        for s in _sessions.values()
    ]}


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    return _sessions[session_id]


@app.post("/api/upload")
async def upload_pdfs(
    files: list[UploadFile] = File(...),
    text_chunk_size: int = Form(512),
    text_chunk_overlap: int = Form(64),
    image_chunk_size: int = Form(256),
    session_id: Optional[str] = Form(None),
):
    """Upload PDFs, extract text/images/tables, build FAISS indices."""
    sid, session = _get_or_create_session(session_id)

    results = []
    for upload in files:
        if not upload.filename.lower().endswith(".pdf"):
            continue

        # Save file
        dest = UPLOAD_DIR / upload.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        session["files"].append(upload.filename)

        # Extract
        text_chunks  = extract_text_chunks(dest, text_chunk_size, text_chunk_overlap)
        image_chunks = extract_images(dest)
        table_chunks = extract_tables(dest)
        all_chunks   = text_chunks + table_chunks + image_chunks

        # Ground truth
        gt = extract_ground_truth(dest)
        session["ground_truths"][upload.filename] = gt

        # Build index
        idx_info = build_index(all_chunks, upload.filename)
        session["indices"][upload.filename] = idx_info

        results.append({
            "filename": upload.filename,
            "text_chunks": len(text_chunks),
            "image_chunks": len(image_chunks),
            "table_chunks": len(table_chunks),
            "total_chunks": len(all_chunks),
            "ground_truth_pairs": len(gt),
            **idx_info,
        })

    return {"session_id": sid, "results": results}


@app.post("/api/query")
async def query_rag(
    query: str = Form(...),
    session_id: str = Form(...),
    models: str = Form(...),          # comma-separated model IDs
    top_k: int = Form(5),
    cosine_threshold: float = Form(0.0),
    temperature: float = Form(0.3),
    run_benchmark: bool = Form(False),
):
    """Query the RAG pipeline with selected models."""
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            400,
            "OPENROUTER_API_KEY is not set. Please set it in your .env file "
            "and restart the server."
        )
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    session = _sessions[session_id]
    if not session["indices"]:
        raise HTTPException(400, "No PDFs indexed in this session")

    model_ids = [m.strip() for m in models.split(",") if m.strip()]

    # Retrieve from all indexed PDFs
    all_retrieved: list[dict] = []
    for pdf_name in session["indices"]:
        try:
            chunks = query_index(query, pdf_name, top_k, cosine_threshold)
            all_retrieved.extend(chunks)
        except FileNotFoundError:
            continue

    # Sort by score globally and take top_k
    all_retrieved.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_chunks = all_retrieved[:top_k]

    # Build context
    context_parts = []
    for i, chunk in enumerate(top_chunks, 1):
        context_parts.append(
            f"[Source: {chunk['source']}, Page {chunk['page']}, "
            f"Score: {chunk['score']:.3f}]\n{chunk['text']}"
        )
    context_str = "\n\n---\n\n".join(context_parts)

    system_prompt = (
        "You are a precise academic research assistant. Answer the question "
        "based ONLY on the provided context. Cite the source file and page "
        "number for each claim. If the context does not contain the answer, "
        "say so explicitly.\n\n"
        f"Context:\n{context_str}"
    )

    # Query each model
    model_results = []
    for model_id in model_ids:
        try:
            llm_resp = await chat_completion(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=temperature,
            )

            result_entry = {
                "model": model_id,
                "answer": llm_resp["content"],
                "latency_s": llm_resp["latency_s"],
                "usage": llm_resp["usage"],
                "sources": [
                    {"source": c["source"], "page": c["page"],
                     "score": c["score"], "type": c.get("type", "text")}
                    for c in top_chunks
                ],
                "context_used": context_str,
            }

            # Benchmark if requested
            if run_benchmark:
                # Find best matching ground truth
                all_gt = []
                for gt_list in session["ground_truths"].values():
                    all_gt.extend(gt_list)
                reference = _find_best_reference(query, all_gt)
                if reference:
                    bench = run_full_benchmark(
                        query, llm_resp["content"],
                        reference, top_chunks,
                    )
                    result_entry["benchmark"] = bench
                    result_entry["reference_answer"] = reference
                else:
                    result_entry["benchmark"] = None
                    result_entry["reference_answer"] = None

            model_results.append(result_entry)
        except Exception as e:
            model_results.append({
                "model": model_id,
                "error": str(e),
            })

    # Save to chat history
    chat_entry = {
        "id": str(uuid.uuid4())[:8],
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "models": model_ids,
        "top_k": top_k,
        "temperature": temperature,
        "results": model_results,
    }
    session["chats"].append(chat_entry)

    return {"session_id": session_id, "chat": chat_entry}


@app.post("/api/benchmark")
async def run_benchmark_endpoint(
    session_id: str = Form(...),
    model: str = Form(...),
    top_k: int = Form(5),
    cosine_threshold: float = Form(0.0),
    temperature: float = Form(0.3),
    max_questions: int = Form(10),
):
    """Run full benchmark using extracted ground truths."""
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            400,
            "OPENROUTER_API_KEY is not set. Please set it in your .env file "
            "and restart the server."
        )
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    session = _sessions[session_id]

    all_gt: list[dict] = []
    for gt_list in session["ground_truths"].values():
        all_gt.extend(gt_list)

    if not all_gt:
        raise HTTPException(400, "No ground truth found in uploaded PDFs")

    benchmark_results = []
    for gt_item in all_gt[:max_questions]:
        question = gt_item["question"]
        reference = gt_item["answer"]

        # Retrieve
        all_retrieved: list[dict] = []
        for pdf_name in session["indices"]:
            try:
                chunks = query_index(question, pdf_name, top_k, cosine_threshold)
                all_retrieved.extend(chunks)
            except FileNotFoundError:
                continue
        all_retrieved.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_chunks = all_retrieved[:top_k]

        context_parts = []
        for c in top_chunks:
            context_parts.append(f"[{c['source']}, p.{c['page']}]\n{c['text']}")
        context_str = "\n\n".join(context_parts)

        try:
            llm_resp = await chat_completion(
                model=model,
                messages=[
                    {"role": "system", "content": f"Answer based on context:\n{context_str}"},
                    {"role": "user", "content": question},
                ],
                temperature=temperature,
            )
            prediction = llm_resp["content"]
            bench = run_full_benchmark(question, prediction, reference, top_chunks)
            benchmark_results.append({
                "question": question,
                "reference": reference,
                "prediction": prediction,
                "benchmark": bench,
                "latency_s": llm_resp["latency_s"],
            })
        except Exception as e:
            benchmark_results.append({
                "question": question,
                "error": str(e),
            })

    # Aggregate
    agg = _aggregate_benchmarks(benchmark_results)
    result = {
        "session_id": session_id,
        "model": model,
        "num_questions": len(benchmark_results),
        "aggregate": agg,
        "details": benchmark_results,
    }
    session["benchmarks"].append(result)
    return result


@app.get("/api/chat_history/{session_id}")
async def chat_history(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    return {"chats": _sessions[session_id]["chats"]}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _find_best_reference(query: str, ground_truths: list[dict]) -> Optional[str]:
    q_tok = set(query.lower().split())
    best, best_score = None, 0
    for gt in ground_truths:
        gt_tok = set(gt["question"].lower().split())
        overlap = len(q_tok & gt_tok) / max(len(q_tok | gt_tok), 1)
        if overlap > best_score:
            best_score = overlap
            best = gt["answer"]
    return best if best_score > 0.2 else None


def _aggregate_benchmarks(results: list[dict]) -> dict:
    metrics = ["bleu", "faithfulness", "answer_relevancy",
               "context_precision", "context_recall", "mrr", "hit_rate"]
    agg = {}
    valid = [r for r in results if "benchmark" in r and r["benchmark"]]
    if not valid:
        return {}
    for m in metrics:
        vals = [r["benchmark"].get(m, 0) for r in valid]
        agg[m] = {
            "mean": round(sum(vals) / len(vals), 4),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
        }
    rouge_f1s = [r["benchmark"]["rouge_l"]["f1"] for r in valid
                 if "rouge_l" in r["benchmark"]]
    if rouge_f1s:
        agg["rouge_l_f1"] = {
            "mean": round(sum(rouge_f1s) / len(rouge_f1s), 4),
            "min": round(min(rouge_f1s), 4),
            "max": round(max(rouge_f1s), 4),
        }
    latencies = [r.get("latency_s", 0) for r in valid]
    agg["avg_latency_s"] = round(sum(latencies) / max(len(latencies), 1), 2)
    return agg


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
