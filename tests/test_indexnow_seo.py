"""IndexNow key and robots.txt sitemap discovery tests."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from main import INDEXNOW_KEY, app  # noqa: E402

client = TestClient(app)


def test_indexnow_key_txt_returns_plain_text_key():
    response = client.get(f"/{INDEXNOW_KEY}.txt")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == INDEXNOW_KEY


def test_robots_txt_includes_sitemap_line():
    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert "Sitemap: https://agentservices.to/sitemap.xml" in response.text
