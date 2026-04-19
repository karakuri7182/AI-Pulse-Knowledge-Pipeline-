"""AI-Pulse pipeline orchestrator: fetch → evaluate → export."""
import io
import os
import sys
import time
from pathlib import Path

# Windows cp932 対策: stdout/stderr を UTF-8 に強制
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import structlog
from dotenv import load_dotenv

log = structlog.get_logger()


def validate_env() -> None:
    """Shift Left: fail immediately if required env vars are missing."""
    missing = [k for k in ("TAVILY_API_KEY", "GEMINI_API_KEY") if not os.environ.get(k)]
    if missing:
        log.error("env_validation_failed", missing=missing)
        sys.exit(1)
    log.info("env_validation_ok")


def main() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    validate_env()

    # import after env validation so modules can rely on env vars being present
    from evaluator import evaluate_article
    from exporter import export
    from fetcher import fetch_articles

    t_start = time.monotonic()
    log.info("pipeline_start")

    # Step 1: Fetch
    articles = fetch_articles(max_per_query=3)
    log.info("fetch_done", count=len(articles))

    if not articles:
        log.info("no_new_articles")
        return

    # Step 2: Evaluate + Export
    stats = {"obsidian": 0, "skills": 0, "review_queue": 0, "skipped": 0}

    for article in articles:
        try:
            evaluated = evaluate_article(article)
        except Exception as exc:
            log.error("evaluate_failed", title=article.title, error=str(exc))
            stats["skipped"] += 1
            continue

        if evaluated.review_queue:
            stats["review_queue"] += 1
            log.warning(
                "low_confidence_queued",
                title=article.title[:60],
                confidence=evaluated.confidence,
            )

        outputs = export(evaluated)
        if "obsidian" in outputs:
            stats["obsidian"] += 1
        if "skill_folder" in outputs:
            stats["skills"] += 1

    elapsed = time.monotonic() - t_start
    log.info(
        "pipeline_done",
        elapsed_s=round(elapsed, 2),
        obsidian_exported=stats["obsidian"],
        skills_exported=stats["skills"],
        review_queue=stats["review_queue"],
        skipped=stats["skipped"],
    )


if __name__ == "__main__":
    main()
