"""
Integration tests
"""
import base64
from pathlib import Path
from paper2wechat import PaperConverter
from paper2wechat.core.models import Article, ImageInfo


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgN6M6vQAAAAASUVORK5CYII="
)


class TestPaperConverter:
    """Test PaperConverter integration"""
    
    def test_initialization(self):
        """Test converter initialization"""
        converter = PaperConverter(
            style="academic-science",
            max_images=3,
            max_length=3000
        )
        assert converter.style == "academic-science"
        assert converter.max_images == 3
        assert converter.max_length == 3000
    
    def test_set_style(self):
        """Test style change"""
        converter = PaperConverter()
        converter.set_style("academic-trend")
        assert converter.style == "academic-trend"
    
    def test_list_styles(self):
        """Test style listing"""
        styles = PaperConverter.list_styles()
        assert "academic-science" in styles
        assert "academic-tech" in styles
        assert "academic-trend" in styles
        assert "academic-applied" in styles
        assert len(styles) == 4

    def test_prepare_images_for_markdown(self, tmp_path: Path):
        """Test selected images are copied near markdown output"""
        source_image = tmp_path / "source.png"
        source_image.write_bytes(PNG_1X1)

        article = Article(
            title="Image Test",
            content="content",
            style="academic-tech",
            images=[
                ImageInfo(
                    url=str(source_image),
                    caption="Figure 1",
                    position=1,
                    relevance_score=0.9,
                    is_selected=True,
                )
            ],
        )

        converter = PaperConverter(cache_dir=str(tmp_path / "cache"))
        output_path = tmp_path / "outputs" / "article.md"
        converter._prepare_images_for_markdown(article, str(output_path))

        assert article.images[0].url.startswith("assets/article/")
