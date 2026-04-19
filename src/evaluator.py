"""Evaluates articles with Gemini 2.5-flash using structured JSON output."""
import json
import os
import time

import structlog
from google import genai
from google.genai import types

from models import Article, EvaluatedArticle, MonetizationScores

log = structlog.get_logger()

SYSTEM_PROMPT = """あなたはAIツール収益化の専門アナリストです。
与えられた記事を4つの収益化ジャンルでスコアリングし、日本語で要約してください。

ジャンル定義:
- youtube: YouTube動画制作・アバター・サムネイル生成・動画AI活用 (1-5)
- kdp: Kindle電子書籍・AIマンガ・出版自動化 (1-5)
- dev_tools: Vibe Coding・Cursor/Claude Code・MCPサーバー・開発効率化 (1-5)
- automation: ひとり社長業務効率化・n8n/Make/Zapier・法人自動化 (1-5)

スコア基準: 1=無関係, 2=周辺, 3=関連あり, 4=強く関連, 5=コア領域
confidence: モデルの確信度 0.0-1.0
summary: 100文字程度の日本語要約（抽象論禁止・具体的機能を記述）
vibe_prompts: このツールのVibe Coding活用プロンプト案を3つ（スコア最大値が4以上の場合のみ）"""

EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "youtube": {"type": "integer", "minimum": 1, "maximum": 5},
        "kdp": {"type": "integer", "minimum": 1, "maximum": 5},
        "dev_tools": {"type": "integer", "minimum": 1, "maximum": 5},
        "automation": {"type": "integer", "minimum": 1, "maximum": 5},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "summary": {"type": "string"},
        "vibe_prompts": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["youtube", "kdp", "dev_tools", "automation", "confidence", "summary", "vibe_prompts"],
}

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY is not set")
        _client = genai.Client(api_key=api_key)
    return _client


def evaluate_article(article: Article) -> EvaluatedArticle:
    client = _get_client()
    prompt = f"""記事タイトル: {article.title}
URL: {article.url}
本文（抜粋）:
{article.content[:2000]}

上記の記事を評価してください。"""

    t0 = time.monotonic()
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=EVAL_SCHEMA,
                    temperature=0.2,
                ),
            )
            data = json.loads(resp.text)
            break
        except Exception as exc:
            last_exc = exc
            # 429は retryDelay に従う（最低13秒 = 60s/5RPM free tier）
            wait = 40 if "429" in str(exc) else 2 ** attempt
            log.warning("gemini_retry", attempt=attempt + 1, wait_s=wait, error=str(exc)[:120])
            time.sleep(wait)
    else:
        log.error("gemini_failed", title=article.title, error=str(last_exc))
        raise RuntimeError(f"Gemini evaluation failed after 3 attempts: {last_exc}") from last_exc

    # 無料枠 5RPM = 12秒/リクエスト。成功後も待機して次の呼び出しを保護
    time.sleep(13)

    elapsed = time.monotonic() - t0
    scores = MonetizationScores(
        youtube=data["youtube"],
        kdp=data["kdp"],
        dev_tools=data["dev_tools"],
        automation=data["automation"],
    )
    confidence = float(data.get("confidence", 1.0))

    log.info(
        "gemini_eval_done",
        title=article.title[:60],
        max_score=scores.max_score(),
        primary=scores.primary_genre(),
        confidence=confidence,
        elapsed_s=round(elapsed, 2),
    )

    return EvaluatedArticle(
        article=article,
        scores=scores,
        summary=data.get("summary", ""),
        confidence=confidence,
        review_queue=confidence < 0.7,
        vibe_prompts=data.get("vibe_prompts", []),
    )
