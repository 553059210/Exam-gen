"""
text_processor.py
-----------------
Lightweight NLP utilities to normalize article text and extract key entities.

We use rule-based heuristics plus optional spaCy Chinese model if available.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import re

try:
    import spacy  # type: ignore
    _SPACY_AVAILABLE = True
except Exception:
    _SPACY_AVAILABLE = False
    spacy = None  # type: ignore


WHITESPACE_RE = re.compile(r"[\u3000\s]+")
PUNCTUATION_RE = re.compile(r"[，、。；：？！,.!?;:]")
NUMBER_RE = re.compile(r"\d+")
DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
KEY_TERMS = [
    "不得", "应当", "可以", "必须", "禁止", "批准", "备案", "罚款", "责任", "义务",
]


def normalize_text(text: str) -> str:
    text = WHITESPACE_RE.sub(" ", text)
    text = text.replace("\u00A0", " ")
    return text.strip()


def split_sentences(text: str) -> List[str]:
    # Rough Chinese sentence split on 。；！? with preservation
    parts = re.split(r"(?<=[。；！？!?])", text)
    return [p.strip() for p in parts if p and p.strip()]


def extract_entities(text: str) -> Dict:
    """Extract simple entities: numbers, dates, key terms, nouns via spaCy if available."""
    norm = normalize_text(text)
    numbers = NUMBER_RE.findall(norm)
    dates = ["{}年{}月{}日".format(*m) for m in DATE_RE.findall(norm)]
    terms = [t for t in KEY_TERMS if t in norm]

    nouns: List[str] = []
    if _SPACY_AVAILABLE:
        try:
            # Lazy load; users can install zh_core_web_sm or similar
            nlp = spacy.blank("zh") if not hasattr(spacy, "load") else spacy.blank("zh")
            doc = nlp(norm)
            # Without POS model, fallback to heuristic: long tokens as candidates
            nouns = [t.text for t in doc if len(t.text) >= 2]
        except Exception:
            nouns = []

    return {
        "numbers": numbers,
        "dates": dates,
        "terms": terms,
        "nouns": nouns,
        "sentences": split_sentences(norm),
    }


def pick_keywords(entities: Dict, max_k: int = 5) -> List[str]:
    candidates = list(dict.fromkeys(entities.get("terms", []) + entities.get("nouns", [])))
    return candidates[:max_k]


