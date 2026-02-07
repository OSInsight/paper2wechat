"""
Markdown generation module
"""
from .models import Article


class MarkdownGenerator:
    """Generate markdown output for WeChat"""
    
    @staticmethod
    def generate(article: Article) -> str:
        """
        Generate markdown from article
        
        Args:
            article: Article object
        
        Returns:
            Markdown string
        """
        return article.to_markdown()
