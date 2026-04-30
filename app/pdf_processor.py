"""PDF text + image extraction with configurable chunking."""
from __future__ import annotations
import io, hashlib, re
from pathlib import Path
from typing import Optional
from PIL import Image
import pdfplumber
from pypdf import PdfReader

# ── helpers ─────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_text_chunks(pdf_path: str | Path, chunk_size: int = 512,
                        overlap: int = 64) -> list[dict]:
    """Return list of {text, page, chunk_idx, source}."""
    chunks: list[dict] = []
    path = Path(pdf_path)
    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            raw = page.extract_text() or ""
            raw = _clean(raw)
            if not raw:
                continue
            words = raw.split()
            start = 0
            cidx = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_text = " ".join(words[start:end])
                chunks.append({
                    "text": chunk_text,
                    "page": page_num,
                    "chunk_idx": cidx,
                    "source": path.name,
                    "type": "text",
                })
                cidx += 1
                start += chunk_size - overlap
    return chunks


def extract_images(pdf_path: str | Path) -> list[dict]:
    """Extract images from PDF, return metadata and base64."""
    images_meta: list[dict] = []
    path = Path(pdf_path)
    reader = PdfReader(str(path))
    for page_num, page in enumerate(reader.pages, 1):
        try:
            resources = page.get("/Resources")
            if not resources or "/XObject" not in resources:
                continue
            x_objects = resources["/XObject"].get_object()
            for obj_name in x_objects:
                obj = x_objects[obj_name].get_object()
                if obj.get("/Subtype") == "/Image":
                    try:
                        data = obj.get_data()
                        w = obj.get("/Width", 0)
                        h = obj.get("/Height", 0)
                        img_hash = hashlib.md5(data[:1024]).hexdigest()[:12]
                        images_meta.append({
                            "page": page_num,
                            "width": w,
                            "height": h,
                            "hash": img_hash,
                            "source": path.name,
                            "type": "image",
                            "text": f"[Image on page {page_num}, {w}x{h}]",
                        })
                    except Exception:
                        continue
        except Exception:
            # Skip pages with malformed resources
            continue
    return images_meta


def extract_tables(pdf_path: str | Path) -> list[dict]:
    """Extract tables as text chunks."""
    tables_data: list[dict] = []
    path = Path(pdf_path)
    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            for tidx, table in enumerate(tables):
                if not table:
                    continue
                rows = []
                for row in table:
                    cells = [str(c).strip() if c else "" for c in row]
                    rows.append(" | ".join(cells))
                table_text = "\n".join(rows)
                tables_data.append({
                    "text": table_text,
                    "page": page_num,
                    "chunk_idx": tidx,
                    "source": path.name,
                    "type": "table",
                })
    return tables_data


def extract_ground_truth(pdf_path: str | Path) -> list[dict]:
    """
    Heuristic ground-truth extraction.
    Looks for Q&A patterns, headings, bold sentences, and section summaries.
    """
    gt: list[dict] = []
    path = Path(pdf_path)
    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            raw = page.extract_text() or ""
            # Pattern 1: Q: … A: …
            qa_pairs = re.findall(
                r'(?:Q|Question)\s*[:.]?\s*(.+?)\s*(?:A|Answer)\s*[:.]?\s*(.+?)(?=(?:Q|Question)\s*[:\.]|$)',
                raw, re.IGNORECASE | re.DOTALL,
            )
            for q, a in qa_pairs:
                gt.append({
                    "question": _clean(q),
                    "answer": _clean(a),
                    "page": page_num,
                    "source": path.name,
                })
            # Pattern 2: section summaries (bold-like lines followed by text)
            sections = re.findall(
                r'^([A-Z][A-Z\s]{3,50})\n(.+?)(?=\n[A-Z][A-Z\s]{3,50}\n|\Z)',
                raw, re.MULTILINE | re.DOTALL,
            )
            for heading, body in sections:
                body_clean = _clean(body)
                if len(body_clean) > 50:
                    gt.append({
                        "question": f"What is discussed under '{_clean(heading)}'?",
                        "answer": body_clean[:500],
                        "page": page_num,
                        "source": path.name,
                    })
    return gt
