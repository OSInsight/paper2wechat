"""
Paper2WeChat - Convert Arxiv papers to WeChat articles

This package provides tools to convert academic papers from Arxiv
to WeChat Official Account articles with intelligent summarization,
content adaptation, and image processing.
"""

__version__ = "0.1.0"
__author__ = "OSInsight"
__license__ = "MIT"

from .models import Article, Paper
from .converter import PaperConverter

__all__ = [
    "Article",
    "Paper",
    "PaperConverter",
]
