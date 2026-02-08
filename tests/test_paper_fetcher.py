"""
Test for paper fetcher module
"""
import base64
from pathlib import Path
import pytest
from paper2wechat.core.paper_fetcher import PaperFetcher


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgN6M6vQAAAAASUVORK5CYII="
)


class _FakeImage:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data


class _FakePage:
    def __init__(self, images):
        self.images = images


class _FakeReader:
    def __init__(self, pages):
        self.pages = pages


class TestPaperFetcher:
    """Test PaperFetcher class"""
    
    def test_parse_arxiv_url_valid(self):
        """Test parsing valid Arxiv URL"""
        fetcher = PaperFetcher()
        arxiv_id = fetcher.parse_arxiv_url("https://arxiv.org/abs/2301.00000")
        assert arxiv_id == "2301.00000"
    
    def test_parse_arxiv_url_invalid(self):
        """Test parsing invalid URL"""
        fetcher = PaperFetcher()
        with pytest.raises(ValueError):
            fetcher.parse_arxiv_url("https://example.com/paper")
    
    def test_parse_arxiv_id_direct(self):
        """Test parsing bare Arxiv ID"""
        fetcher = PaperFetcher()
        arxiv_id = fetcher.parse_arxiv_url("2301.00000")
        assert arxiv_id == "2301.00000"
    
    def test_fetch_from_pdf_file_not_found(self):
        """Test PDF file not found handling"""
        fetcher = PaperFetcher()
        with pytest.raises(FileNotFoundError):
            fetcher.fetch_from_pdf("./test.pdf")

    def test_detect_image_extension(self):
        """Test image extension detection"""
        fetcher = PaperFetcher()
        assert fetcher._detect_image_extension(PNG_1X1, "figure.png") == ".png"
        assert fetcher._detect_image_extension(b"\xff\xd8\xff\xe0abc", "x.bin") == ".jpg"

    def test_extract_pdf_images(self, tmp_path: Path):
        """Test extracting images from PDF pages"""
        fetcher = PaperFetcher(cache_dir=str(tmp_path))
        reader = _FakeReader(
            pages=[
                _FakePage(images=[_FakeImage(name="img1.png", data=PNG_1X1 * 100)]),
            ]
        )

        images = fetcher._extract_pdf_images(reader, cache_key="unit-test")
        assert len(images) == 1
        assert images[0].url.endswith(".png")
        assert Path(images[0].url).exists()

    def test_normalize_page_text(self):
        """Test page text normalization keeps line structure"""
        raw = "Title\\n\\nAbstract\\nLine one -\\ncontinued\\n\\n3\\n"
        normalized = PaperFetcher._normalize_page_text(raw)
        assert "continued" in normalized
        assert "3" not in normalized.splitlines()

    def test_select_plumber_bbox_merges_fragments(self):
        """Fragmented image blocks should be merged into one figure box."""
        boxes = [
            {"x0": 120, "x1": 240, "top": 300, "bottom": 420},
            {"x0": 250, "x1": 370, "top": 300, "bottom": 420},
            {"x0": 380, "x1": 500, "top": 300, "bottom": 420},
            {"x0": 510, "x1": 630, "top": 300, "bottom": 420},
        ]
        rect = PaperFetcher._select_plumber_figure_bbox(
            caption_top=520,
            page_width=1000,
            page_height=1400,
            header_cutoff=140,
            image_boxes=boxes,
        )
        assert rect is not None
        x0, top, x1, bottom = rect
        assert top >= 140
        assert bottom <= 518
        assert x1 - x0 >= 500

    def test_select_plumber_bbox_fallback_is_narrower(self):
        """Fallback area should avoid capturing excessive page header."""
        rect = PaperFetcher._select_plumber_figure_bbox(
            caption_top=400,
            page_width=1000,
            page_height=1000,
            header_cutoff=100,
            image_boxes=[],
        )
        assert rect is not None
        x0, top, x1, bottom = rect
        assert x0 == 80
        assert x1 == 920
        assert top == 100
        assert bottom == 398
