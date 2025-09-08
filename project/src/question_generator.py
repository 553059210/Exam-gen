"""
question_generator.py
---------------------
Generate exam questions from structured law articles.

Question schema (dict):
{
  'type': 'true_false'|'single'|'multiple'|'fill'|'short',
  'question': str,
  'options': Optional[List[str]],
  'answer': Union[str, List[str]],
  'source': {'file': str, 'article': str},
}
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import random
import re

from . import text_processor as tp


def weighted_sample(articles: List[Dict], weights_cfg: Dict, k: int) -> List[Dict]:
    imp_list = set(weights_cfg.get("important_articles", []) or [])
    imp_w = float(weights_cfg.get("important_weight", 1.0))
    default_w = float(weights_cfg.get("default", 1.0))

    weights: List[float] = []
    for a in articles:
        w = imp_w if a.get("article_no") in imp_list else default_w
        weights.append(w)

    # Sample with replacement to allow enough items; we'll dedupe content later
    population = list(range(len(articles)))
    chosen_idx = random.choices(population, weights=weights, k=min(k, max(1, len(population))))
    return [articles[i] for i in chosen_idx]


def make_true_false(arts: List[Dict], count: int, rng: random.Random) -> List[Dict]:
    results: List[Dict] = []
    seen: set = set()
    for art in arts:
        entities = tp.extract_entities(art["text"])
        for sent in entities["sentences"]:
            if len(results) >= count:
                break
            base = sent
            if base in seen or len(base) < 6:
                continue
            seen.add(base)
            flip = rng.random() < 0.5
            q = base
            if flip:
                # Heuristic negation: swap modal verbs or tweak numbers
                q = negate_statement(base)
            results.append({
                "type": "true_false",
                "question": q,
                "options": ["对", "错"],
                "answer": "对" if not flip else "错",
                "source": {"file": art["source_file"], "article": art["article_no"]},
            })
        if len(results) >= count:
            break
    return results


def negate_statement(s: str) -> str:
    # Simple toggles for modal words and numbers
    swaps = [("应当", "不得"), ("必须", "可以"), ("可以", "不得"), ("不得", "可以"), ("禁止", "允许")]
    for a, b in swaps:
        if a in s:
            return s.replace(a, b, 1)
    # If no modal swap, tweak a number if present
    m = re.search(r"\d+", s)
    if m:
        num = int(m.group(0))
        return s[:m.start()] + str(num + 1) + s[m.end():]
    return s + "（本句可能为错误陈述）"


def make_single_choice(arts: List[Dict], count: int, rng: random.Random) -> List[Dict]:
    results: List[Dict] = []
    seen_q: set = set()
    distractor_pool = build_distractor_pool(arts)
    for art in arts:
        if len(results) >= count:
            break
        entities = tp.extract_entities(art["text"])
        kws = tp.pick_keywords(entities, max_k=5)
        if not kws:
            continue
        stem = rng.choice(entities["sentences"]) if entities["sentences"] else art["text"][:50]
        key = rng.choice(kws)
        correct = f"关于“{key}”的表述符合该法条"
        distractors = sample_distractors(distractor_pool, key, n=3, rng=rng)
        options = [correct] + distractors
        rng.shuffle(options)
        ans = options.index(correct)
        qtext = f"依据{art['article_no']}，下列哪一项是正确的？\n{stem}"
        if qtext in seen_q:
            continue
        seen_q.add(qtext)
        results.append({
            "type": "single",
            "question": qtext,
            "options": options,
            "answer": chr(ord('A') + ans),
            "source": {"file": art["source_file"], "article": art["article_no"]},
        })
    return results


def make_multiple_choice(arts: List[Dict], count: int, rng: random.Random) -> List[Dict]:
    results: List[Dict] = []
    distractor_pool = build_distractor_pool(arts)
    for art in arts:
        if len(results) >= count:
            break
        entities = tp.extract_entities(art["text"])
        kws = tp.pick_keywords(entities, max_k=6)
        if len(kws) < 2:
            continue
        stem = rng.choice(entities["sentences"]) if entities["sentences"] else art["text"][:50]
        num_correct = rng.randint(2, min(4, len(kws)))
        correct = [f"与“{kw}”相关的规定符合该法条" for kw in rng.sample(kws, num_correct)]
        distractors = sample_distractors(distractor_pool, "|".join(kws), n=5 - num_correct, rng=rng)
        options = correct + distractors
        rng.shuffle(options)
        ans_letters = [chr(ord('A') + i) for i, opt in enumerate(options) if opt in correct]
        qtext = f"依据{art['article_no']}，下列哪些项是正确的？\n{stem}"
        results.append({
            "type": "multiple",
            "question": qtext,
            "options": options,
            "answer": ans_letters,
            "source": {"file": art["source_file"], "article": art["article_no"]},
        })
    return results


def make_fill_blank(arts: List[Dict], count: int, rng: random.Random) -> List[Dict]:
    results: List[Dict] = []
    for art in arts:
        if len(results) >= count:
            break
        entities = tp.extract_entities(art["text"])
        candidates = (entities.get("terms", []) or []) + (entities.get("numbers", []) or [])
        if not candidates:
            continue
        target = rng.choice(candidates)
        sent = rng.choice(entities["sentences"]) if entities["sentences"] else art["text"]
        if target not in sent:
            sent = art["text"]
        blanked = sent.replace(target, "\\rule{2cm}{0.4pt}", 1)
        results.append({
            "type": "fill",
            "question": blanked,
            "options": None,
            "answer": target,
            "source": {"file": art["source_file"], "article": art["article_no"]},
        })
    return results


def make_short_answers(arts: List[Dict], count: int) -> List[Dict]:
    results: List[Dict] = []
    taken = set()
    for art in arts:
        if len(results) >= count:
            break
        if art["article_no"] in taken:
            continue
        taken.add(art["article_no"])
        q = f"简述{art['article_no']}的主要内容或立法目的。"
        results.append({
            "type": "short",
            "question": q,
            "options": None,
            "answer": art["text"],
            "source": {"file": art["source_file"], "article": art["article_no"]},
        })
    return results


def build_distractor_pool(arts: List[Dict]) -> List[str]:
    pool: List[str] = []
    for art in arts:
        ents = tp.extract_entities(art["text"])
        for kw in tp.pick_keywords(ents, max_k=4):
            pool.append(f"关于“{kw}”的表述不符合该法条")
    # De-duplicate
    return list(dict.fromkeys(pool))


def sample_distractors(pool: List[str], key: str, n: int, rng: random.Random) -> List[str]:
    candidates = [p for p in pool if key not in p]
    if len(candidates) < n:
        candidates = pool
    return rng.sample(candidates, min(n, len(candidates)))


def assemble_exam(articles: List[Dict], cfg: Dict, rng: random.Random) -> Dict[str, List[Dict]]:
    counts = cfg.get("counts", {})
    weights = cfg.get("weights", {})

    tf_arts = weighted_sample(articles, weights, k=counts.get("true_false", 0) * 2)
    sc_arts = weighted_sample(articles, weights, k=counts.get("single_choice", 0) * 2)
    mc_arts = weighted_sample(articles, weights, k=counts.get("multiple_choice", 0) * 2)
    fb_arts = weighted_sample(articles, weights, k=counts.get("fill_blank", 0) * 2)

    short_important = [a for a in articles if a.get("article_no") in set(weights.get("important_articles", []))]
    if len(short_important) < counts.get("short_answer", 0):
        short_important = (short_important + articles)[: counts.get("short_answer", 0)]

    exam = {
        "true_false": make_true_false(tf_arts, counts.get("true_false", 0), rng),
        "single": make_single_choice(sc_arts, counts.get("single_choice", 0), rng),
        "multiple": make_multiple_choice(mc_arts, counts.get("multiple_choice", 0), rng),
        "fill": make_fill_blank(fb_arts, counts.get("fill_blank", 0), rng),
        "short": make_short_answers(short_important, counts.get("short_answer", 0)),
    }
    return exam


