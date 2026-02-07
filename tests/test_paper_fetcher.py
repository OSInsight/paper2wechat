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
