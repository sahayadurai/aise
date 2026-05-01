"""FastAPI application — RAG Benchmark PDF Data Extractor."""
from __future__ import annotations
import json, uuid, shutil, time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as DBSession

from app.config import (
    UPLOAD_DIR, INDEX_DIR, RESULTS_DIR, CHAT_DIR,
    AVAILABLE_MODELS, HOST, PORT, OPENROUTER_API_KEY,
)
from app.database import init_db, get_db, Session, UploadedFile as DBUploadedFile, ChatMessage, GroundTruth, Benchmark
from app.pdf_processor import (
    extract_text_chunks, extract_images, extract_tables, extract_ground_truth,
)
from app.embeddings import build_index, query_index
from app.llm_client import chat_completion
from app.benchmarks import run_full_benchmark

app = FastAPI(title="RAG Benchmark PDF Data Extractor", version="1.0.0")

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        init_db()
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")


# ── Session Management ──────────────────────────────────────────────────────

def _get_or_create_session_db(session_id: Optional[str] = None, db: DBSession = None) -> tuple[str, Session]:
    """Get or create session in database."""
    if not db:
        db = next(get_db())
    
    if session_id:
        session = db.query(Session).filter(Session.id == session_id).first()
        if session:
            return session.id, session
    
    # Create new session
    sid = session_id or str(uuid.uuid4())[:8]
    new_session = Session(id=sid)
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return sid, new_session


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
async def list_sessions(db: DBSession = Depends(get_db)):
    """List all sessions."""
    sessions = db.query(Session).all()
    return {"sessions": [
        {
            "id": s.id,
            "files": len(s.files),
            "chats": len(s.chats),
            "created": s.created_at.isoformat() if s.created_at else None
        }
        for s in sessions
    ]}


@app.get("/api/session/{session_id}")
async def get_session(session_id: str, db: DBSession = Depends(get_db)):
    """Get session details."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "id": session.id,
        "files": [f.to_dict() for f in session.files],
        "chats_count": len(session.chats),
        "benchmarks_count": len(session.benchmarks),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@app.post("/api/upload")
async def upload_pdfs(
    files: list[UploadFile] = File(...),
    text_chunk_size: int = Form(512),
    text_chunk_overlap: int = Form(64),
    image_chunk_size: int = Form(256),
    session_id: Optional[str] = Form(None),
    db: DBSession = Depends(get_db),
):
    """Upload PDFs, extract text/images/tables, build FAISS indices."""
    sid, session = _get_or_create_session_db(session_id, db)

    results = []
    for upload in files:
        if not upload.filename.lower().endswith(".pdf"):
            continue

        # Save file
        dest = UPLOAD_DIR / upload.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)
        
        file_size = dest.stat().st_size

        # Extract
        text_chunks = extract_text_chunks(dest, text_chunk_size, text_chunk_overlap)
        image_chunks = extract_images(dest)
        table_chunks = extract_tables(dest)
        all_chunks = text_chunks + table_chunks + image_chunks

        # Ground truth
        gt = extract_ground_truth(dest)

        # Build index
        idx_info = build_index(all_chunks, upload.filename)

        # Create database record
        file_record = DBUploadedFile(
            id=str(uuid.uuid4()),
            session_id=sid,
            filename=upload.filename,
            file_path=str(dest),
            file_size=file_size,
            text_chunks_count=len(text_chunks),
            image_chunks_count=len(image_chunks),
            table_chunks_count=len(table_chunks),
            ground_truth_count=len(gt),
            text_chunk_size=text_chunk_size,
            text_chunk_overlap=text_chunk_overlap,
            image_chunk_size=image_chunk_size,
            index_path=idx_info.get("index_path"),
            metadata_path=idx_info.get("metadata_path"),
            index_status="indexed" if idx_info.get("index_path") else "error",
        )
        db.add(file_record)
        db.flush()

        # Store ground truth records
        for gt_item in gt:
            gt_record = GroundTruth(
                id=str(uuid.uuid4()),
                file_id=file_record.id,
                question=gt_item.get("question", ""),
                answer=gt_item.get("answer", ""),
                extraction_method=gt_item.get("method", "unknown"),
            )
            db.add(gt_record)

        db.commit()

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
    db: DBSession = Depends(get_db),
):
    """Query the RAG pipeline with selected models."""
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            400,
            "OPENROUTER_API_KEY is not set. Please set it in your .env file "
            "and restart the server."
        )
    
    # Get session from DB
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    if not session.files:
        raise HTTPException(400, "No PDFs indexed in this session")

    model_ids = [m.strip() for m in models.split(",") if m.strip()]

    # Retrieve from all indexed PDFs
    all_retrieved: list[dict] = []
    for pdf_file in session.files:
        try:
            chunks = query_index(query, pdf_file.filename, top_k, cosine_threshold)
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
                for pdf_file in session.files:
                    all_gt.extend(pdf_file.ground_truths)
                reference = _find_best_reference(query, [{"question": gt.question, "answer": gt.answer} for gt in all_gt])
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

    # Save to chat history in DB
    chat_entry = ChatMessage(
        id=str(uuid.uuid4())[:8],
        session_id=session_id,
        query=query,
        top_k=top_k,
        temperature=int(temperature * 10),  # Store as int*10
        cosine_threshold=int(cosine_threshold * 100),  # Store as int*100
        model_ids=",".join(model_ids),
        responses=model_results,
        run_benchmark=run_benchmark,
    )
    db.add(chat_entry)
    db.commit()

    return {"session_id": session_id, "chat": {
        "id": chat_entry.id,
        "query": chat_entry.query,
        "timestamp": chat_entry.timestamp.isoformat() if chat_entry.timestamp else None,
        "models": model_ids,
        "top_k": top_k,
        "temperature": temperature,
        "results": model_results,
    }}


@app.post("/api/benchmark")
async def run_benchmark_endpoint(
    session_id: str = Form(...),
    model: str = Form(...),
    top_k: int = Form(5),
    cosine_threshold: float = Form(0.0),
    temperature: float = Form(0.3),
    max_questions: int = Form(10),
    db: DBSession = Depends(get_db),
):
    """Run full benchmark using extracted ground truths."""
    if not OPENROUTER_API_KEY:
        raise HTTPException(
            400,
            "OPENROUTER_API_KEY is not set. Please set it in your .env file "
            "and restart the server."
        )
    
    # Get session from DB
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    # Collect all ground truths from uploaded files
    all_gt: list[dict] = []
    for pdf_file in session.files:
        for gt in pdf_file.ground_truths:
            all_gt.append({
                "question": gt.question,
                "answer": gt.answer,
            })

    if not all_gt:
        raise HTTPException(400, "No ground truth found in uploaded PDFs")

    benchmark_results = []
    for gt_item in all_gt[:max_questions]:
        question = gt_item["question"]
        reference = gt_item["answer"]

        # Retrieve
        all_retrieved: list[dict] = []
        for pdf_file in session.files:
            try:
                chunks = query_index(question, pdf_file.filename, top_k, cosine_threshold)
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
    
    # Save to DB
    benchmark_record = Benchmark(
        id=str(uuid.uuid4()),
        session_id=session_id,
        model_id=model,
        max_questions=max_questions,
        top_k=top_k,
        aggregate_metrics=agg,
        detailed_results=benchmark_results,
    )
    db.add(benchmark_record)
    db.commit()
    
    result = {
        "session_id": session_id,
        "model": model,
        "num_questions": len(benchmark_results),
        "aggregate": agg,
        "details": benchmark_results,
    }
    return result


@app.get("/api/chat_history/{session_id}")
async def chat_history(session_id: str, db: DBSession = Depends(get_db)):
    """Get chat history for a session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return {"chats": [chat.to_dict() for chat in session.chats]}


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
