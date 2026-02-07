"""
Paper2WeChat - Convert Arxiv papers to WeChat articles

This is the main public API module.
"""

from .core.models import Article, Paper
from .core.converter import PaperConverter

__version__ = "0.1.0"
__all__ = [
    "PaperConverter",
    "Article", 
    "Paper",
]
