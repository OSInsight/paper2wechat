"""
Image processing module - extract and process paper images
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import List
from .models import ImageInfo

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None


class ImageProcessor:
    """Process and select images from papers"""
    
    def __init__(self, max_images: int = 5):
        """
        Initialize processor
        
        Args:
            max_images: Maximum images to select
        """
        self.max_images = max_images
    
    def select_images(self, images: List[ImageInfo], content: str) -> List[ImageInfo]:
        """
        Select most relevant images
        
        Args:
            images: Available images from paper
            content: Article content for relevance matching
        
        Returns:
            List of selected images (up to max_images)
        """
        if not images or self.max_images <= 0:
            return []

        content_lower = content.lower()
        for image in images:
            if image.relevance_score <= 0:
                image.relevance_score = 0.5
            caption_tokens = self._caption_tokens(image.caption)
            overlap = sum(1 for token in caption_tokens if token in content_lower)
            if overlap:
                image.relevance_score = min(1.0, image.relevance_score + overlap * 0.03)

        ranked = sorted(
            images,
            key=lambda img: (-img.relevance_score, img.position),
        )
        selected = ranked[: self.max_images]

        for img in ranked:
            img.is_selected = False
        for img in selected:
            img.is_selected = True

        return selected
    
    @staticmethod
    def compress_image(image_path: str, output_path: str, max_width: int = 1920) -> None:
        """
        Compress image for WeChat
        
        Args:
            image_path: Input image
            output_path: Output image
            max_width: Maximum width in pixels
        """
        src = Path(image_path)
        dst = Path(output_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        if Image is None:
            shutil.copyfile(src, dst)
            return

        with Image.open(src) as image:
            if image.width > max_width:
                ratio = max_width / float(image.width)
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height))

            suffix = dst.suffix.lower()
            if suffix in {".jpg", ".jpeg"} and image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")

            save_format = "PNG" if suffix == ".png" else "JPEG"
            save_kwargs = {"optimize": True}
            if save_format == "JPEG":
                save_kwargs["quality"] = 85

            image.save(dst, format=save_format, **save_kwargs)

    @staticmethod
    def _caption_tokens(caption: str) -> List[str]:
        return [
            token
            for token in re.findall(r"[a-zA-Z]{3,}", caption.lower())
            if token not in {"figure", "image", "page"}
        ]
