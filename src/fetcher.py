"""Fetches latest AI tool articles via Tavily API with SQLite deduplication."""
import hashlib
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import structlog
from tavily import TavilyClient

from models import Article

log = structlog.get_logger()

DB_PATH = Path(__file__).parent.parent / "outputs" / "seen_urls.db"

QUERIES = [
    "latest AI video generation tools 2026",
    "AI KDP Kindle publishing automation 2026",
    "Claude Code Cursor Windsurf vibe coding 2026",
    "n8n Make.com AI automation workflow 2026",
    "AI エージェント ひとり社長 自動化 2026",
]


def _init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS seen (url_hash TEXT PRIMARY KEY, url TEXT, seen_at TEXT)"
    )
    conn.commit()
    return conn


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _is_seen(conn: sqlite3.Connection, url: str) -> bool:
    h = _url_hash(url)
    return conn.execute("SELECT 1 FROM seen WHERE url_hash=?", (h,)).fetchone() is not None


def _mark_seen(conn: sqlite3.Connection, url: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO seen VALUES (?,?,?)",
        (_url_hash(url), url, datetime.utcnow().isoformat()),
    )
    conn.commit()


def fetch_articles(max_per_query: int = 3) -> list[Article]:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise EnvironmentError("TAVILY_API_KEY is not set")

    client = TavilyClient(api_key=api_key)
    conn = _init_db()
    articles: list[Article] = []

    for query in QUERIES:
        t0 = time.monotonic()
        try:
            resp = client.search(
                query=query,
                search_depth="advanced",
                time_range="week",
                max_results=max_per_query,
            )
        except Exception as exc:
            log.error("tavily_search_failed", query=query, error=str(exc))
            raise

        elapsed = time.monotonic() - t0
        results = resp.get("results", [])
        new_count = 0

        for r in results:
            url = r.get("url", "")
            if not url or _is_seen(conn, url):
                continue
            _mark_seen(conn, url)
            articles.append(
                Article(
                    title=r.get("title", ""),
                    url=url,
                    content=r.get("content", ""),
                    published_date=r.get("published_date"),
                    source=r.get("url", "").split("/")[2] if url else None,
                )
            )
            new_count += 1

        log.info(
            "tavily_query_done",
            query=query,
            new=new_count,
            total_results=len(results),
            elapsed_s=round(elapsed, 2),
        )

    conn.close()
    log.info("fetch_complete", total_new_articles=len(articles))
    return articles
