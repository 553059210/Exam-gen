"""
docx_parser.py
----------------
Utilities to read .docx law documents and extract structured articles.

Assumptions:
- Articles start with a heading like "第X条" possibly followed by 标题.
- Within articles, paragraphs may contain 款/项; we keep simple hierarchy.

Output structure:
List[{
    'source_file': str,
    'article_no': str,          # e.g., '第12条'
    'title': str,               # optional short title if detected
    'text': str,                # full concatenated text of the article
    'clauses': List[str],       # split by 款/项 heuristics
}]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
import re
from pathlib import Path

from docx import Document


ARTICLE_PATTERN = re.compile(r"^第[一二三四五六七八九十百千0-9]+条")
CLAUSE_SPLIT_PATTERN = re.compile(r"[（(][一二三四五六七八九十0-9]+[)）]|第[一二三四五六七八九十0-9]+款")


@dataclass
class Article:
    source_file: str
    article_no: str
    title: str
    text: str
    clauses: List[str]

    def to_dict(self) -> Dict:
        return {
            "source_file": self.source_file,
            "article_no": self.article_no,
            "title": self.title,
            "text": self.text,
            "clauses": self.clauses,
        }


def read_docx(file_path: Path) -> List[Article]:
    doc = Document(str(file_path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]

    articles: List[Article] = []
    current_no = None
    current_title = ""
    buffer: List[str] = []

    def flush_article():
        nonlocal current_no, current_title, buffer
        if current_no is None:
            return
        full_text = "\n".join(buffer).strip()
        clauses = split_clauses(full_text)
        articles.append(
            Article(
                source_file=str(file_path.name),
                article_no=current_no,
                title=current_title,
                text=full_text,
                clauses=clauses,
            )
        )
        current_no = None
        current_title = ""
        buffer = []

    for para in paragraphs:
        if ARTICLE_PATTERN.match(para):
            # Start of a new article
            flush_article()
            # Extract article number and optional title
            m = ARTICLE_PATTERN.match(para)
            assert m is not None
            current_no = m.group(0)
            current_title = para[m.end():].strip(" 　：:.-")
            if current_title and len(current_title) > 50:
                # Likely not a title but continuation
                buffer.append(para)
                current_title = ""
        else:
            if current_no is None:
                # Skip preface text
                continue
            buffer.append(para)

    # Flush last article
    flush_article()
    return articles


def split_clauses(text: str) -> List[str]:
    # Heuristic: split by line breaks first, then further by 款/项 markers
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    chunks: List[str] = []
    for line in lines:
        parts = re.split(r"(?=(?:第[一二三四五六七八九十0-9]+款|[（(][一二三四五六七八九十0-9]+[)）]))", line)
        for part in parts:
            part = part.strip()
            if part:
                chunks.append(part)
    return chunks or ([text] if text else [])


def parse_directory(input_dir: str) -> List[Dict]:
    path = Path(input_dir)
    all_articles: List[Dict] = []
    for file in path.glob("*.docx"):
        try:
            arts = read_docx(file)
            all_articles.extend([a.to_dict() for a in arts])
        except Exception as exc:
            # Skip problematic files but continue
            print(f"[docx_parser] Failed to read {file}: {exc}")
    return all_articles


