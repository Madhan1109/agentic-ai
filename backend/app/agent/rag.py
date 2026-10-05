"""HR policy knowledge retrieval (RAG) with BM25 fallback + optional Chroma/OpenAI embeddings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from backend.app.config import get_settings


@dataclass
class PolicyChunk:
    source: str
    title: str
    text: str


def _split_markdown(text: str, source: str) -> list[PolicyChunk]:
    parts = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    chunks: list[PolicyChunk] = []
    doc_title = Path(source).stem.replace("_", " ").title()
    for part in parts:
        part = part.strip()
        if not part:
            continue
        first_line = part.splitlines()[0].lstrip("# ").strip()
        title = first_line or doc_title
        # Further chunk long sections
        if len(part) > 1200:
            paragraphs = [p.strip() for p in part.split("\n\n") if p.strip()]
            buf = ""
            for p in paragraphs:
                if len(buf) + len(p) > 900 and buf:
                    chunks.append(PolicyChunk(source=source, title=title, text=buf.strip()))
                    buf = p
                else:
                    buf = f"{buf}\n\n{p}".strip()
            if buf:
                chunks.append(PolicyChunk(source=source, title=title, text=buf.strip()))
        else:
            chunks.append(PolicyChunk(source=source, title=title, text=part))
    return chunks


def load_policy_chunks(policies_dir: str | None = None) -> list[PolicyChunk]:
    settings = get_settings()
    root = Path(policies_dir or settings.policies_dir)
    chunks: list[PolicyChunk] = []
    for path in sorted(root.glob("*.md")):
        chunks.extend(_split_markdown(path.read_text(encoding="utf-8"), path.name))
    return chunks


class PolicyRetriever:
    """Simple, dependency-light retriever suitable for demos and offline indexing."""

    def __init__(self, chunks: list[PolicyChunk] | None = None):
        self.chunks = chunks or load_policy_chunks()
        tokenized = [self._tokenize(c.text) for c in self.chunks]
        self._bm25 = BM25Okapi(tokenized) if self.chunks else None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def search(self, query: str, k: int = 4) -> list[dict]:
        if not self.chunks or not self._bm25:
            return []
        scores = self._bm25.get_scores(self._tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
        results = []
        for idx, score in ranked:
            if score <= 0:
                continue
            chunk = self.chunks[idx]
            results.append(
                {
                    "source": chunk.source,
                    "title": chunk.title,
                    "excerpt": chunk.text[:900],
                    "score": float(score),
                }
            )
        return results


@lru_cache
def get_retriever() -> PolicyRetriever:
    return PolicyRetriever()


def format_policy_context(hits: list[dict]) -> str:
    if not hits:
        return "No matching policy sections found."
    blocks = []
    for i, hit in enumerate(hits, 1):
        blocks.append(
            f"[{i}] Source: {hit['source']} | Section: {hit['title']}\n{hit['excerpt']}"
        )
    return "\n\n---\n\n".join(blocks)
