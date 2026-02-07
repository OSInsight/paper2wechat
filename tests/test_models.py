"""
Test models
"""
from paper2wechat.core.models import Article, Paper, Section, ImageInfo


class TestArticle:
    """Test Article model"""
    
    def test_creation(self):
        """Test article creation"""
        article = Article(
            title="Test Article",
            content="Test content",
            style="academic-tech",
            word_count=100
        )
        assert article.title == "Test Article"
        assert article.content == "Test content"
        assert article.style == "academic-tech"
    
    def test_preview(self):
        """Test preview generation"""
        article = Article(
            title="Test",
            content="A" * 600,  # 600 character content
            style="academic-tech"
        )
        preview = article.preview(max_length=500)
        assert len(preview) <= 503  # 500 chars + "..."
        assert preview.endswith("...")
    
    def test_to_markdown(self):
        """Test markdown conversion"""
        article = Article(
            title="Test Article",
            content="Test content paragraph 1\n\nTest content paragraph 2",
            style="academic-tech",
            summary="This is a test"
        )
        markdown = article.to_markdown()
        assert "# Test Article" in markdown
        assert "Test content paragraph 1" in markdown
        assert "This is a test" in markdown


class TestPaper:
    """Test Paper model"""
    
    def test_creation(self):
        """Test paper creation"""
        paper = Paper(
            title="Test Paper",
            authors=["Author One", "Author Two"],
            abstract="Test abstract"
        )
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 2
    
    def test_full_text(self):
        """Test full text property"""
        section = Section(
            title="Introduction",
            content="This is the introduction.",
            level=2
        )
        paper = Paper(
            title="Test Paper",
            sections=[section],
            abstract="Test abstract"
        )
        full_text = paper.full_text
        assert "Test Paper" in full_text
        assert "Test abstract" in full_text
        assert "Introduction" in full_text


class TestImageInfo:
    """Test ImageInfo model"""
    
    def test_creation(self):
        """Test image info creation"""
        image = ImageInfo(
            url="https://example.com/image.jpg",
            caption="Test image",
            position=1,
            relevance_score=0.8
        )
        assert image.url == "https://example.com/image.jpg"
        assert image.relevance_score == 0.8
        assert not image.is_selected
