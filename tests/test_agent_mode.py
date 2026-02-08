"""
Tests for agent mode request parsing.
"""
from paper2wechat.core.agent_mode import parse_agent_request


class TestAgentMode:
    def test_parse_direct_url(self):
        intent = parse_agent_request("https://arxiv.org/abs/2510.21603")
        assert intent.source == "https://arxiv.org/abs/2510.21603"
        assert intent.style == "academic-tech"
        assert intent.images == 5
        assert intent.max_length == 5000

    def test_parse_natural_language_constraints(self):
        intent = parse_agent_request(
            "把 2510.21603 转成偏趋势风，4张图，3000字以内，输出 outputs/x.md"
        )
        assert intent.source == "2510.21603"
        assert intent.style == "academic-trend"
        assert intent.images == 4
        assert intent.max_length == 3000
        assert intent.output == "outputs/x.md"

    def test_parse_prefers_pdf_path_over_embedded_id(self):
        intent = parse_agent_request(
            "把 .paper2wechat/downloads/2510.21603.pdf 转成技术风文章，4张图"
        )
        assert intent.source == ".paper2wechat/downloads/2510.21603.pdf"
