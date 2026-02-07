"""
Content adaptation module - convert academic to WeChat format
"""
from __future__ import annotations

import re
from typing import List


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
    
    def adapt(self, content: str, max_length: int = 5000) -> str:
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

        limited = self._truncate_to_words(normalized, max_length=max_length)
        paragraphs = self._to_paragraphs(limited, chunk_size=140)
        key_points = self._extract_key_points(limited, max_items=4)

        intro = self.prompts.get(self.style, self.prompts["academic-tech"])
        lines = [
            intro["headline"],
            "",
            intro["tone"],
            "",
            "## 核心内容",
            "",
            *paragraphs,
        ]

        if key_points:
            lines.extend(["", "## 关键信息", ""])
            lines.extend([f"- {point}" for point in key_points])

        return "\n".join(lines).strip()
    
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
            },
            "academic-tech": {
                "headline": "## 从论文到工程：技术视角解读",
                "tone": "重点看方法怎么落地、复杂度如何变化、工程价值在哪里。",
            },
            "academic-trend": {
                "headline": "## 从论文到趋势：前沿视角解读",
                "tone": "重点关注新方向、新能力，以及它可能改变什么。",
            },
            "academic-applied": {
                "headline": "## 从论文到应用：产业视角解读",
                "tone": "重点关注可落地场景、成本收益和业务影响。",
            },
        }

    @staticmethod
    def _normalize_content(content: str) -> str:
        text = content.replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    @staticmethod
    def _truncate_to_words(text: str, max_length: int) -> str:
        if max_length <= 0:
            return ""

        words = text.split()
        if len(words) <= max_length:
            return text

        sentences = re.split(r"(?<=[.!?。！？])\s+", text)
        selected: List[str] = []
        used = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            length = len(sentence.split())
            if used + length > max_length:
                break
            selected.append(sentence)
            used += length

        if not selected:
            return " ".join(words[:max_length])
        return " ".join(selected)

    @staticmethod
    def _to_paragraphs(text: str, chunk_size: int = 140) -> List[str]:
        words = text.split()
        paragraphs: List[str] = []
        for start in range(0, len(words), chunk_size):
            chunk = words[start : start + chunk_size]
            if chunk:
                paragraphs.append(" ".join(chunk))
        return paragraphs

    @staticmethod
    def _extract_key_points(text: str, max_items: int = 4) -> List[str]:
        sentences = re.split(r"(?<=[.!?。！？])\s+", text)
        points: List[str] = []
        for sentence in sentences:
            clean = sentence.strip()
            word_count = len(clean.split())
            if word_count < 8 or word_count > 45:
                continue
            points.append(clean)
            if len(points) >= max_items:
                break
        return points
