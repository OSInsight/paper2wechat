"""
Main converter class for paper2wechat
"""
from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Optional, List
from .models import Article
from .paper_fetcher import PaperFetcher
from .content_adapter import ContentAdapter
from .image_processor import ImageProcessor
from .markdown_generator import MarkdownGenerator


class PaperConverter:
    """Main class for converting papers to WeChat articles"""
    
    def __init__(
        self,
        style: str = "academic-tech",
        max_images: int = 5,
        max_length: int = 5000,
        cache_dir: str = ".paper2wechat",
    ):
        """
        Initialize converter
        
        Args:
            style: Conversion style (academic-science, academic-tech, academic-trend, academic-applied)
            max_images: Maximum number of images to include
            max_length: Maximum content length in words
            cache_dir: Working directory for downloads and parsed cache
        """
        self.style = style
        self.max_images = max_images
        self.max_length = max_length
        self.cache_dir = cache_dir
        
        self.fetcher = PaperFetcher(cache_dir=cache_dir)
        self.adapter = ContentAdapter(style=style)
        self.image_processor = ImageProcessor(max_images=max_images)
        self.markdown_generator = MarkdownGenerator()
    
    def convert(self, url: str, output_path: Optional[str] = None) -> Article:
        """
        Convert paper from URL to WeChat article
        
        Args:
            url: Arxiv URL or paper identifier
            output_path: Optional path to save markdown
        
        Returns:
            Article object
        """
        # Fetch paper
        paper = self.fetcher.fetch_from_url(url)
        
        # Adapt content
        adapted_content = self.adapter.adapt(
            paper.full_text,
            max_length=self.max_length
        )
        
        # Process images
        selected_images = self.image_processor.select_images(
            paper.images,
            content=adapted_content
        )
        
        # Generate article
        article = Article(
            title=paper.title,
            content=adapted_content,
            style=self.style,
            original_paper=paper,
            images=selected_images,
            summary=paper.abstract,
            word_count=len(adapted_content.split()),
        )
        
        if output_path:
            self._prepare_images_for_markdown(article, output_path)
            article.save_markdown(output_path)
        
        return article
    
    def convert_pdf(self, pdf_path: str, output_path: Optional[str] = None) -> Article:
        """
        Convert paper from PDF file to WeChat article
        
        Args:
            pdf_path: Path to PDF file
            output_path: Optional path to save markdown
        
        Returns:
            Article object
        """
        # Fetch paper from PDF
        paper = self.fetcher.fetch_from_pdf(pdf_path)
        
        # Same as convert() from here
        adapted_content = self.adapter.adapt(
            paper.full_text,
            max_length=self.max_length
        )
        
        selected_images = self.image_processor.select_images(
            paper.images,
            content=adapted_content
        )
        
        article = Article(
            title=paper.title,
            content=adapted_content,
            style=self.style,
            original_paper=paper,
            images=selected_images,
            summary=paper.abstract,
            word_count=len(adapted_content.split()),
        )
        
        if output_path:
            self._prepare_images_for_markdown(article, output_path)
            article.save_markdown(output_path)
        
        return article
    
    def upload_to_wechat(self, article: Article, draft: bool = True) -> dict:
        """
        Upload article to WeChat (requires configuration)
        
        Args:
            article: Article to upload
            draft: Upload as draft (True) or publish (False)
        
        Returns:
            Result dict with status and media_id
        """
        md2wechat_script = Path("md2wechat/scripts/run.sh")
        if not md2wechat_script.exists():
            return {
                "status": "error",
                "message": "md2wechat not found at md2wechat/scripts/run.sh",
            }

        tmp_dir = Path(self.cache_dir) / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        md_path = tmp_dir / "wechat_upload.md"
        article.save_markdown(str(md_path))

        cmd = ["bash", str(md2wechat_script), "convert", str(md_path)]
        if draft:
            cmd.append("--draft")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {
                "status": "error",
                "code": result.returncode,
                "stderr": (result.stderr or "").strip(),
                "stdout": (result.stdout or "").strip(),
            }

        return {
            "status": "success",
            "code": 0,
            "stdout": (result.stdout or "").strip(),
        }
    
    def set_style(self, style: str) -> None:
        """Change conversion style"""
        self.style = style
        self.adapter.set_style(style)
    
    @staticmethod
    def list_styles() -> List[str]:
        """List available styles"""
        return [
            "academic-science",
            "academic-tech",
            "academic-trend",
            "academic-applied",
        ]

    def _prepare_images_for_markdown(self, article: Article, output_path: str) -> None:
        selected = [img for img in article.images if img.is_selected]
        if not selected:
            return

        md_path = Path(output_path).expanduser().resolve()
        asset_root = md_path.parent / "assets" / md_path.stem
        asset_root.mkdir(parents=True, exist_ok=True)

        for index, image in enumerate(selected, start=1):
            source = Path(image.url).expanduser()
            if not source.is_absolute():
                source = (Path.cwd() / source).resolve()

            if not source.exists() or not source.is_file():
                continue

            suffix = source.suffix.lower() or ".jpg"
            target = asset_root / f"figure_{index:02d}{suffix}"
            if source.resolve() != target.resolve():
                shutil.copyfile(source, target)

            image.url = str(target.relative_to(md_path.parent).as_posix())
