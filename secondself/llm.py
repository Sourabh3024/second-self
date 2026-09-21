"""LLM helpers for SecondSelf classification and future answer synthesis."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from secondself.config import VALID_CATEGORIES, settings

try:  # pragma: no cover - optional dependency for AI features.
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None


def _sanitize_text(text: str) -> str:
    return " ".join(text.split())


def _fallback_tags(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text.lower())
    stop_words = {
        "about", "after", "again", "against", "all", "also", "always", "am", "an",
        "and", "any", "are", "as", "at", "be", "because", "been", "before", "being",
        "between", "both", "but", "by", "can", "could", "did", "do", "does", "doing",
        "down", "during", "each", "few", "for", "from", "further", "had", "has", "have",
        "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
        "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most",
        "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
        "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
        "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
        "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
        "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
        "while", "who", "whom", "why", "with", "you", "your", "yours", "yourself",
        "yourselves", "need", "build", "using", "used", "make", "notes", "note",
    }
    unique: list[str] = []
    for word in words:
        if len(word) < 3 or word in stop_words:
            continue
        if word not in unique:
            unique.append(word)
        if len(unique) >= 6:
            break
    return unique or ["knowledge"]


def _fallback_classification(text: str) -> dict[str, Any]:
    cleaned = _sanitize_text(text).lower()
    if any(term in cleaned for term in [
        "project", "build", "launch", "deadline", "portfolio", "prototype", "pipeline",
        "career", "goal", "research", "ml", "engineering", "roadmap",
    ]):
        category = "Projects"
    elif any(term in cleaned for term in [
        "habit", "routine", "weekly", "review", "system", "responsibility", "health",
        "finance", "personal", "process", "area", "ongoing", "domain",
    ]):
        category = "Areas"
    elif any(term in cleaned for term in [
        "reference", "guide", "resource", "article", "paper", "docs", "tutorial",
        "library", "api", "documentation", "embedding", "vector", "retrieval",
    ]):
        category = "Resources"
    else:
        category = "Archives"

    title = _sanitize_text(text).splitlines()[0][:80] or "Untitled capture"
    summary = _sanitize_text(text)[:180]
    if len(summary) > 180:
        summary = summary[:177].rstrip() + "..."
    return {
        "category": category,
        "tags": _fallback_tags(text),
        "summary": summary or "Captured note needing review.",
        "title": title,
    }


def call_llm(prompt: str, system: str = "") -> str:
    """Call the Groq LLM when configured; otherwise raise a runtime error."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    if Groq is None:
        raise RuntimeError("groq package is not installed")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", settings.llm_model),
        temperature=0.2,
        messages=[
            {"role": "system", "content": system or "You classify personal knowledge notes."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("The LLM returned an empty response")
    return content.strip()


def classify_content(text: str) -> dict[str, Any]:
    """Return a PARA classification with tags and a one-line summary."""
    cleaned = _sanitize_text(text)
    if not cleaned:
        raise ValueError("Text must not be empty")

    prompt = (
        "Classify the following personal knowledge note into exactly one category from: "
        "Projects, Areas, Resources, Archives. "
        "Return strict JSON with keys: category, tags, summary, title. "
        "The tags must be a list of 3-6 short keywords. "
        "The summary must be one sentence. "
        "Use only information in the note.\n\n"
        f"NOTE:\n{cleaned[:8000]}"
    )

    try:
        payload = call_llm(prompt, system="You must answer with valid JSON only.")
        parsed = json.loads(payload)
        category = str(parsed.get("category", "")).strip()
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Invalid PARA category: {category!r}")
        tags = parsed.get("tags")
        if not isinstance(tags, list) or not tags:
            raise ValueError("Classification tags must be a non-empty list")
        summary = str(parsed.get("summary", "")).strip()
        title = str(parsed.get("title", "")).strip()
        if not summary or not title:
            raise ValueError("Classification summary and title are required")
        return {
            "category": category,
            "tags": [str(item).strip() for item in tags][:6],
            "summary": summary[:280],
            "title": title[:80],
        }
    except Exception:
        return _fallback_classification(cleaned)


def synthesize_answer(context: str, question: str) -> str:
    """Answer a question using only the supplied note context."""
    cleaned_question = _sanitize_text(question)
    if not cleaned_question:
        raise ValueError("Question must not be empty")
    cleaned_context = context.strip()
    if not cleaned_context:
        return "I don't have notes about that."

    prompt = (
        "You are SecondSelf, answering from the user's personal knowledge base. "
        "Use ONLY the provided notes. If the answer is not present, say so clearly. "
        "Cite supporting notes using their [note-id] markers. Be concise and factual.\n\n"
        f"NOTES:\n{cleaned_context}\n\nQUESTION:\n{cleaned_question}"
    )
    try:
        return call_llm(
            prompt,
            system="You answer questions from personal notes and must not invent facts.",
        )
    except Exception:
        return _fallback_answer(cleaned_context, cleaned_question)


def _fallback_answer(context: str, question: str) -> str:
    """Provide a deterministic extractive answer when no LLM is configured."""
    question_terms = set(re.findall(r"[A-Za-z0-9]+", question.lower()))
    candidates = []
    for paragraph in context.split("\n"):
        cleaned = paragraph.strip()
        if not cleaned or cleaned.startswith("NOTE ") or cleaned.startswith("---"):
            continue
        paragraph_terms = set(re.findall(r"[A-Za-z0-9]+", cleaned.lower()))
        score = len(question_terms & paragraph_terms)
        candidates.append((score, cleaned))
    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = [text for score, text in candidates if score > 0][:3]
    if not selected:
        return "I don't have notes about that."
    return "Based on your notes: " + " ".join(selected)
