"""
Data models for paper2wechat
"""
from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime


@dataclass
class ImageInfo:
    """Information about an image in the paper"""
    url: str
    caption: str
    position: int  # Position in document
    relevance_score: float = 0.5
    is_selected: bool = False

    def __str__(self):
        return f"Image: {self.caption[:50]}... (relevance: {self.relevance_score:.2f})"


@dataclass
class Section:
    """A section of the paper"""
    title: str
    content: str
    level: int = 1
    images: List[ImageInfo] = field(default_factory=list)

    def __str__(self):
        return f"{'#' * self.level} {self.title}"


@dataclass
class Paper:
    """Metadata and content of an academic paper"""
    title: str
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    published_date: Optional[datetime] = None
    arxiv_id: Optional[str] = None
    pdf_url: Optional[str] = None
    
    # Content
    sections: List[Section] = field(default_factory=list)
    images: List[ImageInfo] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)
    
    # Metadata
    url: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """Concatenate all sections into full text"""
        result = [f"# {self.title}"]
        if self.abstract:
            result.append(f"\n## Abstract\n\n{self.abstract}")
        
        for section in self.sections:
            result.append(f"\n{str(section)}\n\n{section.content}")
        
        return "\n".join(result)

    def __str__(self):
        return f"{self.title} by {', '.join(self.authors) if self.authors else 'Unknown'}"


@dataclass
class Article:
    """Converted WeChat article"""
    title: str
    content: str
    style: str
    original_paper: Optional[Paper] = None
    
    # Content metadata
    word_count: int = 0
    images: List[ImageInfo] = field(default_factory=list)
    sections: List[Section] = field(default_factory=list)
    
    # Processing metadata
    generated_at: datetime = field(default_factory=datetime.now)
    processing_time_seconds: float = 0.0
    
    # Optional fields
    cover_image_url: Optional[str] = None
    cover_image_prompt: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None

    def preview(self, max_length: int = 500) -> str:
        """Get a preview of the article"""
        preview_text = self.content[:max_length]
        if len(self.content) > max_length:
            preview_text += "..."
        return preview_text

    def to_markdown(self) -> str:
        """Convert to markdown format"""
        lines = [f"# {self.title}", ""]
        
        if self.summary:
            lines.append(f"> **Summary**: {self.summary}")
            lines.append("")

        selected_images = [img for img in self.images if img.is_selected]
        content = self.content
        has_image_markdown = self._contains_image_markdown(content)

        if selected_images and not has_image_markdown:
            content = self._inject_images_into_content(content, selected_images)
            has_image_markdown = self._contains_image_markdown(content)

        lines.append(content)

        if selected_images and not has_image_markdown:
            lines.append("\n## Figures\n")
            for img in selected_images:
                lines.append(f"![{img.caption}]({img.url})")
                lines.append(f"_{img.caption}_\n")
        
        return "\n".join(lines)

    def save_markdown(self, filepath: str) -> None:
        """Save article as markdown file"""
        output = Path(filepath)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('w', encoding='utf-8') as f:
            f.write(self.to_markdown())

    @classmethod
    def from_markdown(cls, filepath: str, style: str = "academic-tech") -> "Article":
        """Load article from markdown file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple parsing (can be improved)
        lines = content.split('\n')
        title = lines[0].lstrip('#').strip() if lines[0].startswith('#') else "Untitled"
        
        return cls(
            title=title,
            content=content,
            style=style,
            word_count=len(content.split()),
        )

    def __str__(self):
        return f"Article: {self.title} ({self.word_count} words, {len(self.images)} images)"

    @staticmethod
    def _contains_image_markdown(content: str) -> bool:
        return bool(re.search(r"!\[[^\]]*\]\([^)]+\)", content or ""))

    def _inject_images_into_content(self, content: str, images: List[ImageInfo]) -> str:
        if not content.strip() or not images:
            return content

        lines = content.splitlines()
        heading_indices = [
            idx
            for idx, line in enumerate(lines)
            if line.strip().startswith("## ")
        ]
        if not heading_indices:
            return self._append_images_between_paragraphs(content, images)

        targets = self._select_heading_targets(lines, heading_indices, images)
        grouped: dict[int, List[ImageInfo]] = {}
        for target, image in zip(targets, images):
            grouped.setdefault(target, []).append(image)

        merged: List[str] = []
        for idx, line in enumerate(lines):
            merged.append(line)
            if idx in grouped:
                merged.append("")
                for image in grouped[idx]:
                    merged.extend(self._render_image_block(image))
                    merged.append("")

        return "\n".join(merged).rstrip()

    def _append_images_between_paragraphs(self, content: str, images: List[ImageInfo]) -> str:
        blocks = [block for block in content.split("\n\n")]
        if not blocks:
            return content

        total_blocks = len(blocks)
        targets: List[int] = []
        image_count = len(images)
        for idx in range(image_count):
            target = int(round((idx + 1) * total_blocks / (image_count + 1)))
            target = max(0, min(total_blocks - 1, target))
            targets.append(target)

        grouped: dict[int, List[ImageInfo]] = {}
        for target, image in zip(targets, images):
            grouped.setdefault(target, []).append(image)

        merged: List[str] = []
        for idx, block in enumerate(blocks):
            merged.append(block)
            if idx in grouped:
                for image in grouped[idx]:
                    merged.append("")
                    merged.extend(self._render_image_block(image))

        return "\n\n".join(merged).rstrip()

    def _select_heading_targets(
        self,
        lines: List[str],
        heading_indices: List[int],
        images: List[ImageInfo],
    ) -> List[int]:
        headings = [
            {
                "index": idx,
                "title": re.sub(r"^#{1,6}\s*", "", lines[idx].strip()).lower(),
                "group": self._classify_heading(lines[idx]),
            }
            for idx in heading_indices
        ]

        fallback_targets = self._evenly_distribute_targets(heading_indices, len(images))
        resolved: List[int] = []
        for image_idx, image in enumerate(images):
            group = self._classify_caption(image.caption)
            if group:
                matched = [h["index"] for h in headings if h["group"] == group]
                if matched:
                    resolved.append(matched[0])
                    continue
            resolved.append(fallback_targets[image_idx])
        return resolved

    @staticmethod
    def _evenly_distribute_targets(heading_indices: List[int], image_count: int) -> List[int]:
        if not heading_indices:
            return []
        total = len(heading_indices)
        targets: List[int] = []
        for idx in range(image_count):
            pos = int(round((idx + 1) * total / (image_count + 1))) - 1
            pos = max(0, min(total - 1, pos))
            targets.append(heading_indices[pos])
        return targets

    @staticmethod
    def _classify_caption(caption: str) -> Optional[str]:
        text = (caption or "").lower()
        if any(token in text for token in ("architecture", "framework", "pipeline", "workflow")):
            return "method"
        if any(token in text for token in ("performance", "accuracy", "benchmark", "retrieval", "result")):
            return "result"
        if any(token in text for token in ("use case", "overview", "demo", "annotation", "example")):
            return "intro"
        return None

    @staticmethod
    def _classify_heading(heading: str) -> Optional[str]:
        text = heading.lower()
        if any(token in text for token in ("速览", "背景", "引言", "问题", "overview", "introduction", "why")):
            return "intro"
        if any(token in text for token in ("方法", "架构", "流程", "实现", "method", "architecture", "system")):
            return "method"
        if any(token in text for token in ("实验", "结果", "评测", "性能", "benchmark", "evaluation")):
            return "result"
        return None

    @staticmethod
    def _render_image_block(image: ImageInfo) -> List[str]:
        return [
            f"![{image.caption}]({image.url})",
            f"_{image.caption}_",
        ]
