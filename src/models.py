"""Data models for the AI knowledge pipeline."""
from dataclasses import dataclass, field
from typing import Optional


GENRE_TAGS = {
    "youtube": "#01_Business/YouTube",
    "kdp": "#01_Business/KDP",
    "dev_tools": "#02_Dev/AI_Tools",
    "automation": "#03_Corp/Automation",
}


@dataclass
class Article:
    title: str
    url: str
    content: str
    published_date: Optional[str] = None
    source: Optional[str] = None


@dataclass
class MonetizationScores:
    youtube: int = 0      # YouTube/動画制作
    kdp: int = 0          # 出版/KDP
    dev_tools: int = 0    # 開発効率化
    automation: int = 0   # 法人経営/自動化

    def max_score(self) -> int:
        return max(self.youtube, self.kdp, self.dev_tools, self.automation)

    def primary_genre(self) -> str:
        scores = {
            "youtube": self.youtube,
            "kdp": self.kdp,
            "dev_tools": self.dev_tools,
            "automation": self.automation,
        }
        return max(scores, key=scores.get)

    def primary_tag(self) -> str:
        return GENRE_TAGS[self.primary_genre()]


@dataclass
class EvaluatedArticle:
    article: Article
    scores: MonetizationScores
    summary: str
    confidence: float = 1.0
    review_queue: bool = False
    vibe_prompts: list[str] = field(default_factory=list)
