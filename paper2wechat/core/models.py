"""
Data models for paper2wechat
"""
from dataclasses import dataclass, field
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
        
        lines.append(self.content)
        
        if self.images:
            lines.append("\n## Figures\n")
            for i, img in enumerate(self.images):
                if img.is_selected:
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
