"""Exports evaluated articles to Obsidian markdown and skill folders."""
import os
import re
from datetime import date
from pathlib import Path

import frontmatter
import structlog

from models import EvaluatedArticle

log = structlog.get_logger()

_DEFAULT_OBSIDIAN = Path(__file__).parent.parent / "outputs" / "obsidian"
_DEFAULT_SKILLS = Path(__file__).parent.parent / "outputs" / "skills"

OBSIDIAN_DIR = Path(os.environ.get("OBSIDIAN_OUTPUT_DIR", str(_DEFAULT_OBSIDIAN)))
SKILLS_DIR = Path(os.environ.get("SKILLS_OUTPUT_DIR", str(_DEFAULT_SKILLS)))


def _safe_filename(text: str, max_len: int = 60) -> str:
    """Sanitize text for use as a Windows-safe filename."""
    text = re.sub(r'[\\/:*?"<>|]', "_", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text[:max_len]


def export_obsidian(evaluated: EvaluatedArticle) -> Path:
    OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    safe_title = _safe_filename(evaluated.article.title)
    filename = f"{today}_{safe_title}.md"
    filepath = OBSIDIAN_DIR / filename

    post = frontmatter.Post(
        content=f"## 概要\n\n{evaluated.summary}\n\n## ソース\n\n- [{evaluated.article.title}]({evaluated.article.url})\n",
        title=evaluated.article.title,
        tags=[evaluated.scores.primary_tag()],
        source_url=evaluated.article.url,
        created=today,
        score=evaluated.scores.max_score(),
        category=evaluated.scores.primary_genre(),
        summary=evaluated.summary,
        confidence=round(evaluated.confidence, 2),
        review_queue=evaluated.review_queue,
    )

    filepath.write_text(frontmatter.dumps(post), encoding="utf-8")
    log.info("obsidian_exported", file=filename, score=evaluated.scores.max_score())
    return filepath


def export_skill_folder(evaluated: EvaluatedArticle) -> Path:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(evaluated.article.title)
    skill_dir = SKILLS_DIR / safe_name
    skill_dir.mkdir(exist_ok=True)

    prompts_md = "\n".join(
        f"{i+1}. {p}" for i, p in enumerate(evaluated.vibe_prompts)
    ) if evaluated.vibe_prompts else "- （プロンプト生成スキップ）"

    readme = f"""# {evaluated.article.title}

## 概要

{evaluated.summary}

**収益化スコア**: {evaluated.scores.max_score()}/5 ({evaluated.scores.primary_genre()})
**ソース**: {evaluated.article.url}

## スコア詳細

| ジャンル | スコア |
|---------|--------|
| YouTube/動画制作 | {evaluated.scores.youtube}/5 |
| KDP/出版 | {evaluated.scores.kdp}/5 |
| 開発効率化 | {evaluated.scores.dev_tools}/5 |
| 法人自動化 | {evaluated.scores.automation}/5 |

## Vibe Coding 活用プロンプト

{prompts_md}
"""

    readme_path = skill_dir / "README.md"
    readme_path.write_text(readme, encoding="utf-8")
    log.info("skill_exported", folder=safe_name, score=evaluated.scores.max_score())
    return skill_dir


def export(evaluated: EvaluatedArticle) -> dict:
    result = {}
    max_score = evaluated.scores.max_score()

    if max_score >= 3:
        result["obsidian"] = str(export_obsidian(evaluated))

    if max_score >= 4:
        result["skill_folder"] = str(export_skill_folder(evaluated))

    return result
