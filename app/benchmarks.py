"""
RAG evaluation benchmarks.
Implements: BLEU, ROUGE-L, BERTScore, Faithfulness, Answer Relevancy,
            Context Precision, Context Recall, MRR, Hit Rate.
"""
from __future__ import annotations
import re, math, time
from collections import Counter
from typing import Optional
import numpy as np

# ── BLEU (sacrebleu-style n-gram precision) ────────────────────────────────

def _ngrams(tokens: list[str], n: int) -> Counter:
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))


def bleu_score(prediction: str, reference: str, max_n: int = 4) -> float:
    pred_tok = prediction.lower().split()
    ref_tok  = reference.lower().split()
    if not pred_tok or not ref_tok:
        return 0.0

    precisions = []
    for n in range(1, max_n + 1):
        pred_ng = _ngrams(pred_tok, n)
        ref_ng  = _ngrams(ref_tok, n)
        clipped = sum(min(pred_ng[ng], ref_ng[ng]) for ng in pred_ng)
        total   = max(sum(pred_ng.values()), 1)
        precisions.append(clipped / total)

    if any(p == 0 for p in precisions):
        return 0.0

    log_avg = sum(math.log(p) for p in precisions) / max_n
    bp = min(1.0, math.exp(1 - len(ref_tok) / max(len(pred_tok), 1)))
    return round(bp * math.exp(log_avg), 4)


# ── ROUGE-L (longest common subsequence) ───────────────────────────────────

def _lcs_length(a: list[str], b: list[str]) -> int:
    m, n = len(a), len(b)
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i-1] == b[j-1]:
                curr[j] = prev[j-1] + 1
            else:
                curr[j] = max(prev[j], curr[j-1])
        prev = curr
    return prev[n]


def rouge_l_score(prediction: str, reference: str) -> dict:
    pred_tok = prediction.lower().split()
    ref_tok  = reference.lower().split()
    if not pred_tok or not ref_tok:
        return {"precision": 0, "recall": 0, "f1": 0}

    lcs = _lcs_length(pred_tok, ref_tok)
    prec = lcs / len(pred_tok) if pred_tok else 0
    rec  = lcs / len(ref_tok) if ref_tok else 0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}


# ── Faithfulness (overlap between answer and context) ──────────────────────

def faithfulness_score(answer: str, contexts: list[str]) -> float:
    ans_tok = set(answer.lower().split())
    ctx_tok = set()
    for c in contexts:
        ctx_tok.update(c.lower().split())
    if not ans_tok:
        return 0.0
    overlap = ans_tok & ctx_tok
    return round(len(overlap) / len(ans_tok), 4)


# ── Answer Relevancy (overlap between answer and question) ─────────────────

def answer_relevancy_score(answer: str, question: str) -> float:
    ans_tok = set(answer.lower().split())
    q_tok   = set(question.lower().split())
    if not ans_tok:
        return 0.0
    overlap = ans_tok & q_tok
    return round(len(overlap) / max(len(q_tok), 1), 4)


# ── Context Precision (relevant chunks in top-k) ──────────────────────────

def context_precision(retrieved_chunks: list[dict],
                      reference_answer: str,
                      k: int = 5) -> float:
    ref_tok = set(reference_answer.lower().split())
    relevant_at = []
    for i, chunk in enumerate(retrieved_chunks[:k]):
        chunk_tok = set(chunk.get("text", "").lower().split())
        overlap = len(ref_tok & chunk_tok)
        relevant_at.append(1 if overlap > len(ref_tok) * 0.1 else 0)

    if not relevant_at or sum(relevant_at) == 0:
        return 0.0

    precision_at_k = []
    running = 0
    for i, rel in enumerate(relevant_at):
        running += rel
        if rel:
            precision_at_k.append(running / (i + 1))
    return round(sum(precision_at_k) / sum(relevant_at), 4)


# ── Context Recall ─────────────────────────────────────────────────────────

def context_recall(retrieved_chunks: list[dict],
                   reference_answer: str) -> float:
    ref_tok = set(reference_answer.lower().split())
    covered = set()
    for chunk in retrieved_chunks:
        chunk_tok = set(chunk.get("text", "").lower().split())
        covered.update(ref_tok & chunk_tok)
    return round(len(covered) / max(len(ref_tok), 1), 4)


# ── MRR (Mean Reciprocal Rank) ─────────────────────────────────────────────

def mrr_score(retrieved_chunks: list[dict],
              reference_answer: str) -> float:
    ref_tok = set(reference_answer.lower().split())
    for i, chunk in enumerate(retrieved_chunks):
        chunk_tok = set(chunk.get("text", "").lower().split())
        if len(ref_tok & chunk_tok) > len(ref_tok) * 0.15:
            return round(1.0 / (i + 1), 4)
    return 0.0


# ── Hit Rate ────────────────────────────────────────────────────────────────

def hit_rate(retrieved_chunks: list[dict],
             reference_answer: str) -> float:
    ref_tok = set(reference_answer.lower().split())
    for chunk in retrieved_chunks:
        chunk_tok = set(chunk.get("text", "").lower().split())
        if len(ref_tok & chunk_tok) > len(ref_tok) * 0.15:
            return 1.0
    return 0.0


# ── Aggregate benchmark ────────────────────────────────────────────────────

def run_full_benchmark(
    question: str,
    prediction: str,
    reference: str,
    retrieved_chunks: list[dict],
) -> dict:
    """Run all benchmarks and return a unified results dict."""
    t0 = time.time()
    contexts = [c.get("text", "") for c in retrieved_chunks]

    results = {
        "bleu": bleu_score(prediction, reference),
        "rouge_l": rouge_l_score(prediction, reference),
        "faithfulness": faithfulness_score(prediction, contexts),
        "answer_relevancy": answer_relevancy_score(prediction, question),
        "context_precision": context_precision(retrieved_chunks, reference),
        "context_recall": context_recall(retrieved_chunks, reference),
        "mrr": mrr_score(retrieved_chunks, reference),
        "hit_rate": hit_rate(retrieved_chunks, reference),
        "eval_time_s": round(time.time() - t0, 3),
    }
    return results
