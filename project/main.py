"""
Main entry to generate exams from law .docx files.

Usage:
  python main.py --config /path/to/config.json --seed 2025 --out-prefix exam_01
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from src import docx_parser
from src import question_generator as qg
from src import latex_generator as lg


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Generate law exam LaTeX using exam-zh")
    parser.add_argument("--config", default="/workspace/project/config.json", help="Path to config.json")
    parser.add_argument("--seed", type=int, default=None, help="Random seed override")
    parser.add_argument("--out-prefix", default="exam_01", help="Output file prefix")
    args = parser.parse_args()

    cfg = load_config(args.config)
    seed = args.seed if args.seed is not None else cfg.get("seed", 42)
    random.seed(seed)
    rng = random.Random(seed)

    input_dir = cfg.get("input_dir", ".")
    print(f"[main] Parsing .docx from {input_dir}")
    articles = docx_parser.parse_directory(input_dir)
    if not articles:
        print("[main] No articles found. Please add .docx files.")
        # For empty input, fabricate a tiny sample to allow dry-run
        articles = [{
            "source_file": "sample.docx",
            "article_no": "第1条",
            "title": "总则",
            "text": "公民依法享有权利并履行义务。不得侵犯他人合法权益。违反规定的，应当承担相应责任。",
            "clauses": [
                "公民依法享有权利并履行义务。",
                "不得侵犯他人合法权益。",
                "违反规定的，应当承担相应责任。",
            ],
        },{
            "source_file": "sample.docx",
            "article_no": "第2条",
            "title": "管理",
            "text": "行政机关可以依照法定权限和程序实施行政管理。应当公开、公正、公平。",
            "clauses": [
                "行政机关可以依照法定权限和程序实施行政管理。",
                "应当公开、公正、公平。",
            ],
        }]

    print(f"[main] Loaded {len(articles)} articles")
    exam = qg.assemble_exam(articles, cfg, rng)
    print("[main] Assembled questions:", {k: len(v) for k, v in exam.items()})

    out = lg.write_exam_files(exam, cfg, args.out_prefix)
    print(f"[main] Wrote: {out['exam']}, {out['answers']}")


if __name__ == "__main__":
    main()

