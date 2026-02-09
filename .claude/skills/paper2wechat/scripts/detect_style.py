#!/usr/bin/env python
"""
Recommend paper2wechat style from parsed paper content.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

STYLE_KEYWORDS: Dict[str, Dict[str, float]] = {
    "academic-science": {
        "theorem": 1.8,
        "lemma": 1.8,
        "proof": 1.8,
        "convergence": 1.4,
        "hypothesis": 1.2,
        "ablation": 1.0,
        "significance": 1.0,
        "reproducibility": 1.4,
        "科学": 1.6,
        "严谨": 1.6,
        "定理": 1.8,
        "证明": 1.8,
        "收敛": 1.4,
        "可复现": 1.4,
    },
    "academic-tech": {
        "system": 1.2,
        "architecture": 1.4,
        "framework": 1.4,
        "pipeline": 1.4,
        "implementation": 1.4,
        "latency": 1.4,
        "throughput": 1.4,
        "deployment": 1.4,
        "inference": 1.2,
        "benchmark": 1.0,
        "工程": 1.6,
        "架构": 1.6,
        "实现": 1.6,
        "部署": 1.5,
        "性能": 1.2,
    },
    "academic-trend": {
        "foundation model": 1.8,
        "llm": 1.8,
        "multimodal": 1.6,
        "agent": 1.2,
        "emergent": 1.3,
        "paradigm": 1.5,
        "frontier": 1.4,
        "future": 1.2,
        "趋势": 1.6,
        "前沿": 1.6,
        "范式": 1.5,
        "未来": 1.3,
        "突破": 1.4,
    },
    "academic-applied": {
        "production": 1.5,
        "industry": 1.3,
        "business": 1.5,
        "clinical": 1.6,
        "hospital": 1.6,
        "finance": 1.4,
        "cost": 1.4,
        "roi": 1.6,
        "case study": 1.2,
        "应用": 1.6,
        "落地": 1.8,
        "业务": 1.6,
        "成本": 1.6,
        "临床": 1.6,
    },
}

STYLE_PRIOR = {
    "academic-science": 0.8,
    "academic-tech": 1.0,
    "academic-trend": 0.8,
    "academic-applied": 0.9,
}

STYLE_PRIORITY = [
    "academic-tech",
    "academic-applied",
    "academic-science",
    "academic-trend",
]

INTENT_HINTS: Dict[str, Dict[str, float]] = {
    "academic-science": {
        "严谨": 0.9,
        "理论": 0.8,
        "methodology": 0.8,
        "scientific": 0.8,
    },
    "academic-tech": {
        "工程": 0.9,
        "实现": 0.9,
        "architecture": 0.8,
        "engineering": 0.8,
    },
    "academic-trend": {
        "趋势": 0.9,
        "前沿": 0.8,
        "future": 0.8,
    },
    "academic-applied": {
        "落地": 0.9,
        "应用": 0.8,
        "business": 0.8,
        "roi": 0.8,
    },
}


STYLE_AXES_MAP = {
    "academic-science": "rigor",
    "academic-tech": "engineering",
    "academic-trend": "trend",
    "academic-applied": "applied",
}


def _is_chinese_token(token: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", token))


def _count_token(text: str, token: str) -> int:
    if not token:
        return 0

    if _is_chinese_token(token):
        return text.count(token)

    if " " in token:
        return text.count(token)

    return len(re.findall(rf"\b{re.escape(token)}\b", text))


def _load_paper_text(input_value: str) -> Tuple[str, str]:
    path = Path(input_value)
    if not path.exists() or not path.is_file():
        return input_value.strip(), "raw_text"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return path.read_text(encoding="utf-8", errors="ignore"), "raw_file"

    if not isinstance(payload, dict):
        return json.dumps(payload, ensure_ascii=False), "json"

    title = str(payload.get("title", "") or "")
    abstract = str(payload.get("abstract", "") or "")
    sections = payload.get("sections", []) or []
    images = payload.get("images", []) or []

    section_titles: List[str] = []
    section_contents: List[str] = []
    for section in sections[:10]:
        if not isinstance(section, dict):
            continue
        section_titles.append(str(section.get("title", "") or ""))
        content = str(section.get("content", "") or "")
        section_contents.append(content[:1500])

    captions: List[str] = []
    for image in images[:20]:
        if not isinstance(image, dict):
            continue
        captions.append(str(image.get("caption", "") or ""))

    merged = "\n".join(
        [
            title,
            abstract,
            "\n".join(section_titles),
            "\n".join(section_contents),
            "\n".join(captions),
        ]
    ).strip()

    return merged, "parsed_json"


def _score_style(text: str, intent_hint: str = "") -> Tuple[Dict[str, float], Dict[str, List[str]]]:
    lower = text.lower()
    scores = {style: STYLE_PRIOR.get(style, 0.0) for style in STYLE_KEYWORDS}
    reasons: Dict[str, List[str]] = defaultdict(list)

    for style, token_weights in STYLE_KEYWORDS.items():
        for token, weight in token_weights.items():
            hits = _count_token(lower, token.lower())
            if hits <= 0:
                continue
            capped_hits = min(hits, 4)
            delta = capped_hits * weight
            scores[style] += delta
            reasons[style].append(f"{token} x{hits}")

    if intent_hint.strip():
        hint = intent_hint.lower()
        for style, token_weights in INTENT_HINTS.items():
            for token, weight in token_weights.items():
                hits = _count_token(hint, token.lower())
                if hits <= 0:
                    continue
                scores[style] += min(hits, 3) * weight
                reasons[style].append(f"intent:{token}")

    return scores, reasons


def _confidence_band(confidence: float) -> str:
    if confidence >= 0.78:
        return "high"
    if confidence >= 0.64:
        return "medium"
    return "low"


def _style_axes(scores: Dict[str, float]) -> Dict[str, float]:
    max_score = max(max(scores.values()), 1e-6)
    axes: Dict[str, float] = {
        "rigor": 1.0,
        "engineering": 1.0,
        "trend": 1.0,
        "applied": 1.0,
    }
    for style, score in scores.items():
        axis = STYLE_AXES_MAP[style]
        ratio = max(score, 0.0) / max_score
        axes[axis] = round(1.0 + 4.0 * ratio, 2)
    return axes


def recommend_style(text: str, intent_hint: str = "") -> Dict[str, Any]:
    scores, reasons = _score_style(text, intent_hint=intent_hint)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    top_style, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0

    tied_styles = [style for style, score in ranked if score == top_score]
    if len(tied_styles) > 1:
        for style in STYLE_PRIORITY:
            if style in tied_styles:
                top_style = style
                break

    margin = top_score - second_score
    denominator = max(top_score + second_score, 1e-6)
    confidence = 0.52 + 0.36 * (margin / denominator)
    confidence = max(0.5, min(0.95, confidence))
    confidence = round(confidence, 3)
    band = _confidence_band(confidence)

    explanation = reasons.get(top_style, [])[:6] or ["no strong style signals found"]
    score_board = {k: round(v, 3) for k, v in ranked}
    top_candidates: List[Dict[str, Any]] = []
    for style, score in ranked[:2]:
        top_candidates.append(
            {
                "style": style,
                "score": round(score, 3),
                "reason_signals": reasons.get(style, [])[:4] or ["no strong style signals found"],
            }
        )

    hybrid_style = None
    if len(ranked) > 1:
        close_ratio = margin / max(top_score, 1e-6)
        if close_ratio <= 0.20:
            hybrid_style = f"{ranked[0][0]} + {ranked[1][0]}"

    if band == "high":
        decision_hint = "prefer_top_candidate"
    elif band == "medium":
        decision_hint = "agent_decide_with_top2"
    else:
        decision_hint = "agent_decide_freely"

    return {
        "recommended_style": top_style,  # keep for compatibility with older callers
        "confidence": confidence,
        "confidence_band": band,
        "reason_signals": explanation,
        "top_candidates": top_candidates,
        "hybrid_style_hint": hybrid_style,
        "style_axes": _style_axes(scores),
        "decision_hint": decision_hint,
        "score_board": score_board,
    }


def _format_plain(result: Dict[str, Any], source_kind: str) -> str:
    lines = [
        f"source: {source_kind}",
        f"recommended_style: {result['recommended_style']}",
        f"confidence: {result['confidence']} ({result['confidence_band']})",
        f"decision_hint: {result['decision_hint']}",
    ]

    if result.get("hybrid_style_hint"):
        lines.append(f"hybrid_style_hint: {result['hybrid_style_hint']}")

    lines.append("top_candidates:")
    for candidate in result["top_candidates"]:
        lines.append(f"- {candidate['style']}: {candidate['score']}")
        for reason in candidate["reason_signals"]:
            lines.append(f"  - {reason}")

    lines.append("style_axes (1-5):")
    for axis, score in result["style_axes"].items():
        lines.append(f"- {axis}: {score}")

    lines.append("score_board:")
    for style, score in result["score_board"].items():
        lines.append(f"- {style}: {score}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recommend paper2wechat style from parsed paper content or raw text.",
    )
    parser.add_argument(
        "input",
        help="Parsed JSON path (preferred) or raw text.",
    )
    parser.add_argument(
        "--user-intent",
        default="",
        help="Optional user intent text to mildly bias recommendation.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON.",
    )
    args = parser.parse_args()

    text, source_kind = _load_paper_text(args.input)
    result = recommend_style(text=text, intent_hint=args.user_intent)

    if args.json:
        payload = {
            "source": source_kind,
            **result,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(_format_plain(result, source_kind=source_kind))


if __name__ == "__main__":
    main()
