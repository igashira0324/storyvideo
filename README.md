# StoryVideo: 自律型 AI 動画制作パイプライン

StoryVideo は、テキストの要約（Brief）から、プロット作成、画像生成（T2I）、動画生成（I2V）、AI による品質レビュー、自動再生成、そして最終的な動画編集（Remotion）までを一貫して行う、展示会クオリティの AI 動画制作パイプラインです。

## 重要: ComfyUI ワークフロー形式

StoryVideo で使用する ComfyUI ワークフローは、**必ず API Format で保存してください。**

- **UI Format**: `nodes` / `links` を含む通常の保存形式（.json）。ComfyUI API の `/prompt` エンドポイントでは使用できません。
- **API Format**: `node_id` をキーにしたフラットな JSON 形式。StoryVideo はこちらを使用します。

**保存方法**: ComfyUI の設定で **Dev Mode** を有効化し、**"Save (API Format)"** または **"Export API"** で保存してください。

## セットアップ

### 1. 依存関係のインストール

```bash
# Python 依存関係
pip install -r requirements.txt

# Node 依存関係 (Remotion 用)
cd remotion
npm install
```

### 2. 環境設定 (`.env`)

`.env.example` をコピーして設定ファイルを作成します。

```bash
cp .env.example .env
```

`.env` 内の URL を環境に合わせて編集してください。

```env
COMFYUI_URL=http://127.0.0.1:8188
OLLAMA_URL=http://127.0.0.1:11434
```

### 3. 外部ツールの準備

- **ComfyUI**: LTX-2.3 および SDXL のモデルが配置され、API モードで動作していること。
- **Ollama**: `qwen2.5:14b`（プランニング用）および `minicpm-v`（レビュー用）がインストールされていること。
- **FFmpeg**: 動画処理およびフレーム抽出のために PATH が通っていること。

## 基本的な使い方（フルパイプライン）

以下のステップで、企画から動画完成までを自動実行します。

```bash
# 1. ショットプランの作成 (LLM)
python3 tools/story_planner.py \
  --brief projects/exhibition_pr/brief.md \
  --project projects/exhibition_pr

# 2. 開始画像の生成 (T2I)
python3 tools/generate_start_images.py \
  --project projects/exhibition_pr \
  --preset workflow_presets/sdxl_t2i.json

# 3. 動画クリップの生成 (I2V)
python3 tools/generate_shots.py \
  --project projects/exhibition_pr --skip-existing

# 4. 基本的な整合性チェック
python3 tools/review_shots.py --project projects/exhibition_pr

# 5. AI による品質レビュー (VLM)
python3 tools/ai_review_shots.py \
  --project projects/exhibition_pr --model minicpm-v

# 6. 自動再生成ループ (自己修復)
python3 tools/regenerate_failed_shots.py \
  --project projects/exhibition_pr --max-rounds 3 --auto-review

# 7. Remotion タイムラインへの組み立てとレンダリング
python3 tools/build_remotion_timeline.py \
  --project projects/exhibition_pr --remotion-dir remotion
cd remotion
npm run build
```

## 高度な機能

### ショット間の連続性維持 (Continuity)
前のショットの最終フレームを次のショットの開始画像として自動設定します。
現在の実装は**非破壊的**で、新しい画像は `_continuity.png` として保存されます。

```bash
# 1. 継続性画像の抽出とプラン更新
python3 tools/link_shots_continuity.py --project projects/exhibition_pr

# 2. 影響を受けるショット（2枚目以降）の再生成
python3 tools/generate_shots.py --project projects/exhibition_pr --only shot_002 shot_003 ...

# 3. 再レビューと再合成
# (ステップ 4〜8 を再度実行)
```

### キャラクター & スタイル・バイブル
`projects/<project_dir>/` 内に `character_bible.json` または `style_bible.json` を配置すると、プランナーおよび T2I 生成時にその設定が自動的に反映されます。

## トラブルシューティング

### "missing_node_type" エラーが出る場合
ComfyUI の API ワークフロー JSON に、インストールされていないカスタムノードが含まれています。
1. ComfyUI でワークフローを開き、Group Node/Subgraph があれば展開（Ungroup）します。
2. API Format で保存し直し、プロジェクトの `comfy_workflows/` 内の JSON と差し替えます。

---

*このプロジェクトは、SusHi Tech Tokyo 2026 等の展示会における自律的な映像制作体験を提供するために開発されています。*
