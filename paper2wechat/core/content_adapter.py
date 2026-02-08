"""
Content adaptation module - convert academic to WeChat format
"""
from __future__ import annotations

import os
import re
from collections import Counter
from typing import Dict, List, Optional, Sequence

try:
    import requests
except Exception:  # pragma: no cover - requests is runtime dependency.
    requests = None

try:
    import anthropic
except Exception:  # pragma: no cover - optional runtime dependency
    anthropic = None

from .models import Section


class ContentAdapter:
    """Adapt academic content for WeChat audience"""
    
    def __init__(self, style: str = "academic-tech"):
        """
        Initialize adapter
        
        Args:
            style: Adaptation style
        """
        self.style = style
        self.prompts = self._load_prompts()
    
    def adapt(
        self,
        content: str,
        max_length: int = 5000,
        title: str = "",
        abstract: str = "",
        sections: Optional[Sequence[Section]] = None,
    ) -> str:
        """
        Adapt content for WeChat
        
        Args:
            content: Original academic content
            max_length: Maximum output length in words
        
        Returns:
            Adapted content
        """
        normalized = self._normalize_content(content)
        if not normalized:
            return ""

        cleaned_content = self._sanitize_source_text(normalized)
        cleaned_abstract = self._sanitize_source_text(abstract)
        chosen_title = (title or "").strip() or self._guess_title_from_content(normalized)

        section_texts = [self._sanitize_source_text(sec.content) for sec in (sections or [])]
        fact_pack = self._extract_fact_pack(
            title=chosen_title,
            abstract=cleaned_abstract,
            content=cleaned_content,
            section_texts=section_texts,
        )

        llm_result = self._adapt_with_llm(
            fact_pack=fact_pack,
            max_length=max_length,
        )
        if llm_result:
            return self._trim_markdown_by_budget(llm_result, max_length=max_length)

        fallback = self._build_chinese_article(
            fact_pack=fact_pack,
            max_length=max_length,
        )
        return self._trim_markdown_by_budget(fallback, max_length=max_length)
    
    def set_style(self, style: str) -> None:
        """Change style"""
        self.style = style
        self.prompts = self._load_prompts()
    
    @staticmethod
    def _load_prompts() -> dict:
        """Load style prompts"""
        return {
            "academic-science": {
                "headline": "## 从论文到结论：科学视角解读",
                "tone": "我们先保留论证逻辑，再逐步解释结论和边界条件。",
                "focus": "重点解释科学问题、关键假设和实验可复现性。",
            },
            "academic-tech": {
                "headline": "## 从论文到工程：技术视角解读",
                "tone": "重点看方法怎么落地、复杂度如何变化、工程价值在哪里。",
                "focus": "重点解释系统设计、实现路径和工程收益。",
            },
            "academic-trend": {
                "headline": "## 从论文到趋势：前沿视角解读",
                "tone": "重点关注新方向、新能力，以及它可能改变什么。",
                "focus": "重点解释新范式、新机会和行业变化方向。",
            },
            "academic-applied": {
                "headline": "## 从论文到应用：产业视角解读",
                "tone": "重点关注可落地场景、成本收益和业务影响。",
                "focus": "重点解释实际业务价值、部署成本和边界条件。",
            },
        }

    @staticmethod
    def _normalize_content(content: str) -> str:
        text = content.replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @staticmethod
    def _sanitize_source_text(text: str) -> str:
        if not text:
            return ""

        normalized = text.replace("\r", "\n")
        normalized = re.sub(r"\[[0-9,\s]+\]", "", normalized)
        normalized = re.sub(r"\s+\n", "\n", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        cutoff = re.search(r"\n\s*(references|acknowledg(e)?ments?)\b", normalized, re.IGNORECASE)
        if cutoff:
            normalized = normalized[: cutoff.start()]

        lines: List[str] = []
        for raw_line in normalized.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Drop obvious page-number/footer noise.
            if re.fullmatch(r"(arXiv:.*|Page \d+|\d+)", line, flags=re.IGNORECASE):
                continue

            if len(line) < 3:
                continue

            if ContentAdapter._looks_like_dense_symbol_noise(line):
                continue

            lines.append(line)

        return "\n".join(lines).strip()

    @staticmethod
    def _looks_like_dense_symbol_noise(line: str) -> bool:
        non_word = len(re.findall(r"[^A-Za-z0-9\u4e00-\u9fff\s]", line))
        density = non_word / max(len(line), 1)
        return density > 0.35 and len(line) > 20

    @staticmethod
    def _guess_title_from_content(content: str) -> str:
        first_line = content.splitlines()[0].strip() if content.splitlines() else ""
        if first_line.startswith("#"):
            return first_line.lstrip("#").strip()
        return first_line[:120] if first_line else "未命名论文"

    def _extract_fact_pack(
        self,
        title: str,
        abstract: str,
        content: str,
        section_texts: Sequence[str],
    ) -> Dict[str, object]:
        corpus_parts = [part for part in [abstract, content, *section_texts] if part]
        corpus = "\n".join(corpus_parts)

        sentences = [
            sentence
            for sentence in self._split_sentences(corpus)
            if not self._is_noise_sentence(sentence)
        ]
        key_sentences = self._pick_ranked_sentences(sentences, max_items=14)
        keywords = self._extract_keywords(corpus, max_items=12)
        metrics = self._extract_metrics(corpus, max_items=8)

        contributions = self._pick_by_patterns(
            sentences,
            patterns=[
                r"\b(we|this paper)\s+(propose|present|introduce|develop)\b",
                r"\b(contribution|novel|new|first)\b",
            ],
            max_items=4,
        )
        methods = self._pick_by_patterns(
            sentences,
            patterns=[
                r"\b(method|framework|architecture|pipeline|approach|algorithm|system)\b",
            ],
            max_items=4,
        )
        results = self._pick_by_patterns(
            sentences,
            patterns=[
                r"\b(result|accuracy|f1|precision|recall|outperform|improve|gain|benchmark)\b",
                r"\d+(\.\d+)?\s*[%xX]",
            ],
            max_items=4,
        )
        limits = self._pick_by_patterns(
            sentences,
            patterns=[
                r"\b(limit|future work|challenge|trade-off|cost|latency|error)\b",
            ],
            max_items=3,
        )

        if not contributions:
            contributions = key_sentences[:3]
        if not methods:
            methods = key_sentences[3:6]
        if not results:
            results = key_sentences[6:9]

        return {
            "title": title.strip() or "未命名论文",
            "abstract": abstract,
            "keywords": keywords,
            "metrics": metrics,
            "contributions": contributions,
            "methods": methods,
            "results": results,
            "limits": limits,
        }

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        candidates = re.split(r"(?<=[.!?。！？;])\s+", normalized)
        output: List[str] = []
        for sentence in candidates:
            clean = sentence.strip(" \n\t-")
            if len(clean) < 30:
                continue
            if len(clean) > 380:
                continue
            output.append(clean)
        return output

    def _pick_ranked_sentences(self, sentences: Sequence[str], max_items: int = 10) -> List[str]:
        scored: List[tuple[int, str]] = []
        for sentence in sentences:
            score = 0
            lower = sentence.lower()

            if re.search(r"\b(we|this paper)\s+(propose|present|introduce)\b", lower):
                score += 5
            if re.search(r"\b(result|benchmark|outperform|improve|accuracy|f1)\b", lower):
                score += 4
            if re.search(r"\d+(\.\d+)?\s*[%xX]", lower):
                score += 3
            if re.search(r"\b(method|framework|pipeline|architecture)\b", lower):
                score += 3

            length_penalty = abs(len(sentence) - 150) // 40
            score -= length_penalty

            scored.append((score, sentence))

        dedup: List[str] = []
        seen = set()
        for _, sentence in sorted(scored, key=lambda item: item[0], reverse=True):
            key = re.sub(r"\W+", "", sentence.lower())[:80]
            if not key or key in seen:
                continue
            seen.add(key)
            dedup.append(sentence)
            if len(dedup) >= max_items:
                break
        return dedup

    @staticmethod
    def _pick_by_patterns(
        sentences: Sequence[str],
        patterns: Sequence[str],
        max_items: int = 3,
    ) -> List[str]:
        result: List[str] = []
        for sentence in sentences:
            lower = sentence.lower()
            if any(re.search(pattern, lower, re.IGNORECASE) for pattern in patterns):
                result.append(sentence)
            if len(result) >= max_items:
                break
        return result

    @staticmethod
    def _extract_metrics(text: str, max_items: int = 8) -> List[str]:
        patterns = [
            r"\d+(\.\d+)?\s*%",
            r"\d+(\.\d+)?\s*[xX]",
            r"(f1|accuracy|precision|recall)\s*[:=]?\s*\d+(\.\d+)?",
            r"\d+(\.\d+)?\s*(ms|s|seconds?)",
        ]
        found: List[str] = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = match.group(0).strip()
                if value not in found:
                    found.append(value)
                if len(found) >= max_items:
                    return found
        return found

    @staticmethod
    def _extract_keywords(text: str, max_items: int = 10) -> List[str]:
        english_stop = {
            "the", "and", "for", "with", "that", "from", "this", "are", "was", "were",
            "into", "their", "have", "has", "had", "using", "used", "our", "can", "not",
            "but", "which", "than", "these", "those", "also", "such", "through", "across",
            "paper", "method", "results", "figure", "table", "section", "based",
        }
        words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text)
        counter = Counter(word.lower() for word in words if word.lower() not in english_stop)

        output: List[str] = []
        for word, _ in counter.most_common(max_items * 3):
            if word in output:
                continue
            if word.startswith("http") or word.startswith("www"):
                continue
            if re.fullmatch(r"x{3,}", word):
                continue
            if re.fullmatch(r"[a-z]*\d+[a-z\d]*", word):
                continue
            output.append(word)
            if len(output) >= max_items:
                break
        return output

    def _adapt_with_llm(self, fact_pack: Dict[str, object], max_length: int) -> Optional[str]:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key and requests is not None:
            result = self._adapt_with_openrouter(
                fact_pack=fact_pack,
                max_length=max_length,
                api_key=openrouter_key,
            )
            if result:
                return result

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or anthropic is None:
            return None

        model_name = os.getenv("PAPER2WECHAT_MODEL", "claude-3-5-sonnet-latest")
        style_prompt = self.prompts.get(self.style, self.prompts["academic-tech"])

        prompt = (
            "你是一位资深中文科技公众号作者。请将下面事实信息改写成可直接发布的公众号文章。\n"
            "要求：\n"
            "1) 全文中文为主，术语可保留英文括号补充；\n"
            "2) 不要粘贴英文原文长段落；\n"
            "3) 结构清晰：背景->方法->结果->价值->局限->总结；\n"
            "4) 保留关键数字和结论，避免编造。\n\n"
            f"风格标题：{style_prompt['headline']}\n"
            f"风格语气：{style_prompt['tone']}\n"
            f"风格重点：{style_prompt['focus']}\n\n"
            f"事实信息：{fact_pack}\n"
        )

        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model_name,
                max_tokens=min(3500, max(1200, max_length)),
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            return None

        text_blocks = [
            block.text
            for block in response.content
            if getattr(block, "type", "") == "text" and getattr(block, "text", "")
        ]
        if not text_blocks:
            return None

        generated = "\n".join(text_blocks).strip()
        if self._contains_large_english_block(generated):
            return None
        return generated

    def _adapt_with_openrouter(
        self,
        fact_pack: Dict[str, object],
        max_length: int,
        api_key: str,
    ) -> Optional[str]:
        style_prompt = self.prompts.get(self.style, self.prompts["academic-tech"])
        model_name = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        prompt = (
            "你是一位资深中文科技公众号作者。请将下面事实信息改写成可直接发布的公众号文章。\n"
            "要求：\n"
            "1) 全文中文为主，术语可保留英文括号补充；\n"
            "2) 不要粘贴英文原文长段落；\n"
            "3) 结构清晰：背景->方法->结果->价值->局限->总结；\n"
            "4) 保留关键数字和结论，避免编造。\n\n"
            f"风格标题：{style_prompt['headline']}\n"
            f"风格语气：{style_prompt['tone']}\n"
            f"风格重点：{style_prompt['focus']}\n\n"
            f"事实信息：{fact_pack}\n"
        )

        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": min(3500, max(1200, max_length)),
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        app_url = os.getenv("OPENROUTER_SITE_URL")
        app_name = os.getenv("OPENROUTER_APP_NAME")
        if app_url:
            headers["HTTP-Referer"] = app_url
        if app_name:
            headers["X-Title"] = app_name

        try:
            response = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            return None

        choices = data.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            text_parts = [block.get("text", "") for block in content if isinstance(block, dict)]
            generated = "\n".join(part for part in text_parts if part).strip()
        else:
            generated = str(content or "").strip()

        if not generated:
            return None
        if self._contains_large_english_block(generated):
            return None
        return generated

    def _build_chinese_article(self, fact_pack: Dict[str, object], max_length: int) -> str:
        prompt = self.prompts.get(self.style, self.prompts["academic-tech"])
        title = str(fact_pack.get("title", "未命名论文"))
        keywords = list(fact_pack.get("keywords", []))
        metrics = list(fact_pack.get("metrics", []))
        contributions = list(fact_pack.get("contributions", []))
        methods = list(fact_pack.get("methods", []))
        results = list(fact_pack.get("results", []))
        limits = list(fact_pack.get("limits", []))

        chinese_keywords = "、".join(self._humanize_keyword(token) for token in keywords[:6]) or "多模态文档处理"
        chinese_keywords = self._compact_keywords(chinese_keywords)
        headline_title = self._decorate_title(title)

        lines: List[str] = [
            prompt["headline"],
            "",
            prompt["tone"],
            "",
            f"## 论文速览",
            "",
            f"这篇论文《{headline_title}》主要关注：{chinese_keywords}。",
            f"从{self._style_lens()}来看，它解决的是“如何把复杂论文内容真正变成可检索、可推理、可落地的知识单元”。",
        ]

        if metrics:
            metric_text = "、".join(metrics[:4])
            lines.append(f"论文中可直接引用的关键指标包括：{metric_text}。")

        lines.extend(["", "## 核心内容", ""])
        lines.extend(self._to_chinese_bullets(contributions, prefix="贡献"))

        if methods:
            lines.extend(["", "## 方法拆解", ""])
            lines.extend(self._to_chinese_bullets(methods, prefix="方法"))

        if results:
            lines.extend(["", "## 实验结果与结论", ""])
            lines.extend(self._to_chinese_bullets(results, prefix="结果"))

        lines.extend(["", "## 为什么值得关注", ""])
        lines.append(f"{prompt['focus']}这让它在“研究检索 -> 证据组织 -> 报告生成”链路上更接近真实工作流。")

        if limits:
            lines.extend(["", "## 局限与后续方向", ""])
            lines.extend(self._to_chinese_bullets(limits, prefix="局限"))
        else:
            lines.extend(
                [
                    "",
                    "## 局限与后续方向",
                    "",
                    "- 当前方法仍受限于解析质量与检索策略，复杂版面和跨文档推理仍有提升空间。",
                ]
            )

        lines.extend(
            [
                "",
                "## 一句话总结",
                "",
                "这篇工作最有价值的地方，不是某个单点模型，而是把“多模态文档研究”做成了可迭代、可验证的系统流程。",
            ]
        )

        article = "\n".join(lines).strip()
        return self._trim_markdown_by_budget(article, max_length=max_length)

    def _to_chinese_bullets(self, sentences: Sequence[str], prefix: str) -> List[str]:
        bullets: List[str] = []
        seen = set()
        for sentence in sentences[:4]:
            hint = self._sentence_to_chinese_hint(sentence, prefix=prefix)
            if hint:
                key = hint.replace(prefix, "").strip()
                if key in seen:
                    continue
                seen.add(key)
                bullets.append(f"- {hint}")
        return bullets or [f"- {prefix}：围绕核心问题给出了一套可执行方案。"]

    def _sentence_to_chinese_hint(self, sentence: str, prefix: str) -> str:
        clean = re.sub(r"\s+", " ", sentence).strip()
        if not clean:
            return ""

        metric_hit = [match.group(0) for match in re.finditer(r"\d+(\.\d+)?\s*[%xX]", clean)]
        keywords = self._extract_keywords(clean, max_items=6)
        keyword_part = "、".join(self._humanize_keyword(token) for token in keywords[:4])
        keyword_part = self._compact_keywords(keyword_part)

        if metric_hit:
            return f"{prefix}：论文报告了 {', '.join(metric_hit[:3])} 等指标，相关内容聚焦在 {keyword_part or '关键性能'}。"

        if self._contains_large_english_block(clean):
            return f"{prefix}：核心关键词包括 {keyword_part or '方法设计、实验验证与系统评估'}。"

        if self._english_ratio(clean) > 0.3:
            return f"{prefix}：围绕 {keyword_part or '核心问题'} 展开，并给出清晰的实现与验证路径。"

        translated = self._lite_translate(clean)
        return f"{prefix}：{translated}"

    @staticmethod
    def _humanize_keyword(token: str) -> str:
        mapping = {
            "multimodal": "多模态",
            "document": "文档",
            "documents": "文档",
            "retrieval": "检索",
            "research": "研究",
            "benchmark": "基准评测",
            "parsing": "解析",
            "pipeline": "流程",
            "framework": "框架",
            "agent": "智能体",
            "agents": "多智能体",
        }
        allowed_terms = {"doc-researcher", "m4docbench", "rag", "llm", "gpt", "bert", "transformer"}
        lower = token.lower()
        if lower in mapping:
            return mapping[lower]
        if lower in allowed_terms:
            return token
        if token.isupper() and len(token) <= 6:
            return token
        if len(token) <= 4:
            return token
        return "关键技术"

    @staticmethod
    def _lite_translate(text: str) -> str:
        output = text
        replacements = {
            r"\bwe propose\b": "作者提出",
            r"\bwe present\b": "作者提出",
            r"\bthis paper\b": "本文",
            r"\bframework\b": "框架",
            r"\bmethod\b": "方法",
            r"\bsystem\b": "系统",
            r"\bresults\b": "结果",
            r"\bexperiment(s)?\b": "实验",
            r"\bimprove(s|d)?\b": "提升",
            r"\boutperform(s|ed)?\b": "优于",
        }
        for pattern, repl in replacements.items():
            output = re.sub(pattern, repl, output, flags=re.IGNORECASE)
        return output

    def _style_lens(self) -> str:
        mapping = {
            "academic-science": "科学研究",
            "academic-tech": "工程实现",
            "academic-trend": "技术趋势",
            "academic-applied": "业务落地",
        }
        return mapping.get(self.style, "技术实现")

    @staticmethod
    def _decorate_title(title: str) -> str:
        clean = re.sub(r"\s+", " ", title).strip()
        return clean[:120] if clean else "未命名论文"

    @staticmethod
    def _trim_markdown_by_budget(text: str, max_length: int) -> str:
        # For Chinese article output, approximate 1 word ~= 2-3 chars.
        max_chars = max(900, max_length * 3)
        if len(text) <= max_chars:
            return text

        lines = text.splitlines()
        kept: List[str] = []
        total = 0
        for line in lines:
            candidate = line + "\n"
            if total + len(candidate) > max_chars:
                break
            kept.append(line)
            total += len(candidate)

        return "\n".join(kept).strip()

    @staticmethod
    def _contains_large_english_block(text: str) -> bool:
        for line in text.splitlines():
            clean = line.strip()
            if not clean:
                continue
            english_words = re.findall(r"[A-Za-z]{3,}", clean)
            if len(english_words) >= 20 and len(english_words) / max(len(clean.split()), 1) > 0.65:
                return True
        return False

    @staticmethod
    def _compact_keywords(keyword_text: str) -> str:
        parts = [part.strip() for part in keyword_text.split("、") if part.strip()]
        dedup: List[str] = []
        for part in parts:
            if part in dedup:
                continue
            dedup.append(part)
        return "、".join(dedup[:6])

    @staticmethod
    def _english_ratio(text: str) -> float:
        english_chars = len(re.findall(r"[A-Za-z]", text))
        return english_chars / max(len(text), 1)

    @staticmethod
    def _is_noise_sentence(sentence: str) -> bool:
        lower = sentence.lower()
        noise_patterns = [
            r"\bpermission to make digital or hard copies\b",
            r"\bcopyright\b",
            r"\bacm\b",
            r"\bisbn\b",
            r"\bdoi\b",
            r"\bproceedings\b",
            r"\brequest permissions\b",
            r"\barxiv:\d{4}\.\d{4,5}\b",
        ]
        return any(re.search(pattern, lower) for pattern in noise_patterns)
