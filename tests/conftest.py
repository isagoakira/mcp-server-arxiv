"""Pytest fixtures for arxiv_mcp_server tests."""
import pytest

from arxiv_mcp_server.utils.arxiv_api import ArxivClient


@pytest.fixture
def arxiv_client():
    """Create an ArxivClient instance for testing."""
    return ArxivClient()


@pytest.fixture
def sample_xml():
    """Real arXiv Atom XML fragment for mocking."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Sample Paper Title</title>
    <summary>This is a sample abstract for testing the arxiv API parsing.</summary>
    <author><name>Test Author</name></author>
    <author><name>Another Author</name></author>
    <published>2023-01-01T00:00:00Z</published>
    <updated>2023-01-15T00:00:00Z</updated>
    <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
    <category term="cs.CV" primary="true"/>
    <category term="cs.LG"/>
    <arxiv:comment xmlns:arxiv="http://arxiv.org/schemas/atom">33 pages, 8 figures</arxiv:comment>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.48550/arXiv.2301.00001</arxiv:doi>
  </entry>
</feed>"""


@pytest.fixture
def sample_xml_multi():
    """Multiple entries XML for pagination testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>First Paper Title</title>
    <summary>First paper abstract.</summary>
    <author><name>Author One</name></author>
    <published>2023-01-01T00:00:00Z</published>
    <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
    <category term="cs.CV"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00002v1</id>
    <title>Second Paper Title</title>
    <summary>Second paper abstract.</summary>
    <author><name>Author Two</name></author>
    <published>2023-02-01T00:00:00Z</published>
    <link title="pdf" href="https://arxiv.org/pdf/2301.00002v1"/>
    <category term="cs.LG"/>
  </entry>
</feed>"""