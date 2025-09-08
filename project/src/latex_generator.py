"""
latex_generator.py
------------------
Render LaTeX exam files using exam-zh style.

We produce two .tex files: exam (no answers) and answers (with \printanswers).
"""

from __future__ import annotations

from typing import Dict, List
from pathlib import Path


HEADER_TMPL = r"""
\documentclass[12pt]{ctexart}
\usepackage[a4paper,margin=2cm]{geometry}
\usepackage{exam-zh}
\usepackage{enumitem}
\usepackage{xeCJK}
\setCJKmainfont{Noto Serif CJK SC}

% Toggle answers with \printanswers
% The answers version will add \printanswers after \begin{document}

\begin{document}
\vspace*{-2em}
\begin{center}
  {\LARGE %TITLE%}\\[4pt]
  考试时间：%TIME%分钟 \quad 满分：%TOTAL%分
\end{center}
\vspace{0.5em}

"""


FOOTER_TMPL = r"""
\end{document}
"""


def _points_sum(points_cfg: Dict, counts_cfg: Dict) -> int:
    return (
        points_cfg.get("true_false", 0) * counts_cfg.get("true_false", 0)
        + points_cfg.get("single_choice", 0) * counts_cfg.get("single_choice", 0)
        + points_cfg.get("multiple_choice", 0) * counts_cfg.get("multiple_choice", 0)
        + points_cfg.get("fill_blank", 0) * counts_cfg.get("fill_blank", 0)
        + points_cfg.get("short_answer", 0) * counts_cfg.get("short_answer", 0)
    )


def render_exam_latex(exam: Dict[str, List[Dict]], cfg: Dict, with_answers: bool) -> str:
    title = cfg.get("exam_title", "考试试卷")
    total = _points_sum(cfg.get("points", {}), cfg.get("counts", {}))
    header = HEADER_TMPL.replace("%TITLE%", title).replace("%TIME%", str(cfg.get("exam_time_minutes", 120))).replace("%TOTAL%", str(total))

    body = []

    def section(title: str):
        body.append(f"\\section*{{{title}}}")

    def render_choices(options: List[str]) -> str:
        items = "\n".join([f"\\item {opt}" for opt in options])
        return f"\\begin{{enumerate}}[label=\\Alph*.]\n{items}\n\\end{{enumerate}}"

    # True/False
    if exam.get("true_false"):
        section("一、判断题")
        body.append("\\begin{questions}")
        for q in exam["true_false"]:
            ans = q["answer"]
            body.append("\\question {}\\ifprintanswers\\par\\textbf{答案：}" + ans + "\\fi".format(latex_escape(q["question"])) )
        body.append("\\end{questions}")

    # Single choice
    if exam.get("single"):
        section("二、单选题")
        body.append("\\begin{questions}")
        for q in exam["single"]:
            body.append("\\question {}".format(latex_escape(q["question"])) )
            body.append(render_choices([latex_escape(o) for o in q["options"]]))
            body.append("\\ifprintanswers\\par\\textbf{答案：}" + latex_escape(q["answer"]) + "\\fi")
        body.append("\\end{questions}")

    # Multiple choice
    if exam.get("multiple"):
        section("三、多选题")
        body.append("\\begin{questions}")
        for q in exam["multiple"]:
            body.append("\\question {}".format(latex_escape(q["question"])) )
            body.append(render_choices([latex_escape(o) for o in q["options"]]))
            body.append("\\ifprintanswers\\par\\textbf{答案：}" + ",".join(q["answer"]) + "\\fi")
        body.append("\\end{questions}")

    # Fill in the blank
    if exam.get("fill"):
        section("四、填空题")
        body.append("\\begin{questions}")
        for q in exam["fill"]:
            body.append("\\question {}".format(latex_escape(q["question"])) )
            body.append("\\ifprintanswers\\par\\textbf{答案：}" + latex_escape(str(q["answer"])) + "\\fi")
        body.append("\\end{questions}")

    # Short answers
    if exam.get("short"):
        section("五、简答题")
        body.append("\\begin{questions}")
        for q in exam["short"]:
            body.append("\\question {}".format(latex_escape(q["question"])) )
            body.append("\\ifprintanswers\\par\\textbf{要点：}" + latex_escape(q["answer"]) + "\\fi")
        body.append("\\end{questions}")

    content = "\n".join(body)
    if with_answers:
        # Insert \printanswers after \begin{document}
        header = header.replace("\\begin{document}", "\\begin{document}\n\\printanswers")
    else:
        # Ensure answers hidden
        header = header.replace("\\usepackage{exam-zh}", "\\usepackage[answers=false]{exam-zh}")

    return header + content + "\n" + FOOTER_TMPL


def write_exam_files(exam: Dict[str, List[Dict]], cfg: Dict, out_prefix: str) -> Dict[str, str]:
    out_dir = Path(cfg.get("output_dir", "."))
    out_dir.mkdir(parents=True, exist_ok=True)
    exam_tex = render_exam_latex(exam, cfg, with_answers=False)
    ans_tex = render_exam_latex(exam, cfg, with_answers=True)

    f1 = out_dir / f"{out_prefix}.tex"
    f2 = out_dir / f"{out_prefix}_answers.tex"
    f1.write_text(exam_tex, encoding="utf-8")
    f2.write_text(ans_tex, encoding="utf-8")
    return {"exam": str(f1), "answers": str(f2)}


def latex_escape(s: str) -> str:
    # Minimal escaping for LaTeX special chars
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in s:
        out.append(repl.get(ch, ch))
    return "".join(out)


