import os
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())

from fastapi.testclient import TestClient
from app import app

c = TestClient(app)


def test_canonical_job_paths_serve_spa_shell():
    for path in ("/runspace/my-bot", "/runspace/my-bot/logs", "/runspace/my-bot/details",
                 "/runspace/my-bot/database", "/runspace/my-bot/env", "/runspace/my-bot/settings"):
        r = c.get(path, headers={"Accept": "text/html"})
        assert r.status_code == 200, path
        assert "<html" in r.text.lower()


def test_legacy_paths_still_serve_shell():
    for path in ("/runspace/owner/my-bot", "/runspace/owner/my-bot/page",
                 "/runspace/owner/my-bot/logs"):
        assert c.get(path).status_code == 200
