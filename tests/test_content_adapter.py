"""
Test for content adapter module
"""
from paper2wechat.core.content_adapter import ContentAdapter


class TestContentAdapter:
    """Test ContentAdapter class"""
    
    def test_initialization(self):
        """Test adapter initialization"""
        adapter = ContentAdapter(style="academic-tech")
        assert adapter.style == "academic-tech"
    
    def test_set_style(self):
        """Test changing style"""
        adapter = ContentAdapter()
        adapter.set_style("academic-science")
        assert adapter.style == "academic-science"
    
    def test_adapt_returns_content(self):
        """Test adapt returns transformed content"""
        adapter = ContentAdapter()
        result = adapter.adapt("This paper introduces a new method. It improves efficiency.")
        assert "核心内容" in result
        assert len(result) > 0
