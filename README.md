# AI-Pulse Monetization-Driven Knowledge Pipeline

最新AIツール情報を自動収集し、収益化スコアで分類してObsidianとGitHubスキルフォルダに出力するパイプライン。

---

## できること

| 機能 | 内容 |
|------|------|
| 最新記事の自動収集 | Tavily APIで5クエリ×最大3件/週の新着AIツール情報を取得 |
| 収益化スコアリング | Gemini 2.5-flashが4ジャンルを1〜5点で自動評価 |
| 重複排除 | SQLiteでURLを管理し、処理済み記事は自動スキップ |
| Obsidian出力 | スコア3以上の記事をYAML frontmatter付きMarkdownで保存 |
| スキルフォルダ出力 | スコア4以上の記事にVibe Codingプロンプト付きREADMEを生成 |
| 自動実行 | GitHub Actionsで毎朝JST 9:00に定期実行 |

### 収益化ジャンル（4分類）

| タグ | ジャンル | 対象 |
|------|---------|------|
| `#01_Business/YouTube` | YouTube・動画制作 | AI動画生成・アバター・サムネイル |
| `#01_Business/KDP` | 出版・メディア | Kindle自動出版・AIマンガ制作 |
| `#02_Dev/AI_Tools` | 開発効率化 | Vibe Coding・Cursor・Claude Code・MCP |
| `#03_Corp/Automation` | 法人経営・自動化 | n8n・Make・ひとり社長業務効率化 |

---

## セットアップ

### 1. APIキーを取得

| サービス | 取得先 | 無料枠 |
|---------|--------|--------|
| Tavily API | https://app.tavily.com/home | 1,000クレジット/月 |
| Gemini API | https://aistudio.google.com/apikey | 5リクエスト/分 |

### 2. `.env` ファイルを作成

プロジェクトルートに `.env` を作成して以下を記述：

```
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSy-xxxxxxxxxxxxxxxxxxxx
```

**Obsidian連携する場合（任意）：**

```
OBSIDIAN_OUTPUT_DIR=G:\マイドライブ\Obsidian Vault\AI-Pulse
```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. 実行

```bash
python src/main.py
```

---

## 出力ファイルの使い方

### Obsidian連携

`outputs/obsidian/` に以下の形式でMarkdownが生成されます：

```yaml
---
title: "Canva AI Video Editing 2026 New Features"
tags: ["#01_Business/YouTube"]
source_url: "https://..."
created: "2026-04-20"
score: 5
category: "youtube"
summary: "Canvaが2026年に追加したAI動画編集機能。..."
---
```

**Obsidianでの表示方法：**
1. Obsidianを開く
2. 設定 → ファイルとリンク → 新しいノートの作成場所 を `outputs/obsidian/` に設定
   または `.env` に `OBSIDIAN_OUTPUT_DIR=<Vault内のフォルダパス>` を設定してパイプラインを実行
3. タグパネルで `#01_Business/YouTube` などをクリックして記事を絞り込む

### スキルフォルダ活用（Vibe Coding）

`outputs/skills/<ツール名>/README.md` にVibe Codingプロンプトが生成されます。

**使い方：**
1. `outputs/skills/` フォルダを開く
2. 気になるツールの `README.md` を開く
3. 「Vibe Coding 活用プロンプト」セクションのプロンプトをコピー
4. Cursor・Claude Code・Windsurf などに貼り付けて実行

**例（Claude Code vs Cursor README より）：**
> 複数のファイルにまたがる大規模なリファクタリングタスク（例: レガシーなデータアクセス層を新しいORMに移行）をClaude Codeで効率的に実行するためのステップバイステップの指示とコードスニペットを提案してください。

---

## GitHub Actionsで自動実行

### Secretsの登録

1. https://github.com/karakuri7182/AI-Pulse-Knowledge-Pipeline-/settings/secrets/actions を開く
2. 「New repository secret」で以下を追加：

| Name | Value |
|------|-------|
| `TAVILY_API_KEY` | `.env` の `TAVILY_API_KEY` の値 |
| `GEMINI_API_KEY` | `.env` の `GEMINI_API_KEY` の値 |

### 実行スケジュール

- **自動実行**: 毎日 UTC 00:00（JST 09:00）
- **手動実行**: GitHubリポジトリ → Actions タブ → 「AI-Pulse Daily Pipeline」→「Run workflow」

### 実行後の確認

毎回の実行結果は `outputs/` に自動コミットされます。
Actions タブでログとステータスを確認できます。

---

## ディレクトリ構成

```
.
├── src/
│   ├── main.py          # オーケストレーター（Shift Left環境チェック）
│   ├── fetcher.py       # Tavily API連携・SQLite重複排除
│   ├── evaluator.py     # Gemini 2.5-flash 構造化JSONスコアリング
│   ├── exporter.py      # Obsidian / スキルフォルダ出力
│   └── models.py        # データクラス定義
├── outputs/
│   ├── obsidian/        # Obsidian用Markdown（score≥3）
│   └── skills/          # Vibe Codingプロンプト付きREADME（score≥4）
├── .github/
│   └── workflows/
│       └── pipeline.yml # GitHub Actions定義
├── requirements.txt
└── .env                 # APIキー（git管理外）
```

---

## コスト目安

| フェーズ | 月額 |
|---------|------|
| Phase 1（週1回手動実行） | 実質 $0（全API無料枠内） |
| Phase 2（毎日自動実行） | $0〜1 |
| Phase 3（クエリ拡張・Web UI追加） | $30〜35 |

---

## トラブルシューティング

**`env_validation_failed` が表示される**
→ `.env` ファイルが存在しないか、APIキーが未設定。

**`no_new_articles` が表示される**
→ 同日中に既に全URLを処理済み。翌日実行するか `outputs/seen_urls.db` を削除すると再取得できる。

**Gemini 429エラーが出る**
→ 無料枠（5リクエスト/分）超過。パイプラインは40秒待機して自動リトライします。

**Obsidianに反映されない**
→ `.env` の `OBSIDIAN_OUTPUT_DIR` のパスを確認。Googleドライブの場合はパスが正確か確認。
