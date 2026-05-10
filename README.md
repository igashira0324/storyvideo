# StoryVideo: 自律型 AI 動画制作パイプライン

StoryVideo は、テキストの要約（Brief）から、プロット作成、画像生成（T2I）、動画生成（I2V）、AI による品質レビュー、自動再生成、そして最終的な動画編集（Remotion）までを一貫して行う、展示会クオリティの AI 動画制作パイプラインです。

## 主な機能

- **自律型ストーリープランナー**: LLM を使用して、短い指示からマルチショットの構成案（ショットプラン）を自動作成します。
- **マルチモーダル生成**: ComfyUI をバックエンドに使用し、SDXL による開始画像生成と LTX-2.3 による高品質な動画生成を統合しています。
- **自己修復ループ (Self-Healing)**: AI（VLM）が生成物をレビューし、品質が低い場合はシード値を更新して自動的に再生成を繰り返します。
- **ショット間の連続性維持 (Continuity)**: 前のショットの最終フレームを次のショットの開始画像として自動的に使用し、一貫性のある映像を実現します。
- **キャラクター/スタイル・バイブル**: キャラクター設定や画風を定義した JSON を読み込ませることで、作品全体の一貫性を保ちます。
- **Remotion 統合**: 生成されたクリップ、字幕、トランジションを自動的に Remotion タイムラインへ組み立て、即座にレンダリング可能です。

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

`.env` ファイルを作成し、各サーバーの URL を設定します。

```env
COMFYUI_URL=http://127.0.0.1:8188
OLLAMA_URL=http://127.0.0.1:11434
```

### 3. 外部ツールの準備

- **ComfyUI**: LTX-2.3 および SDXL のモデルが配置され、API モードで動作していること。
- **Ollama**: `qwen2.5:14b`（プランニング用）および `minicpm-v`（レビュー用）がインストールされていること。
- **FFmpeg**: 動画処理およびフレーム抽出のために PATH が通っていること。

## 基本的な使い方（フルパイプライン）

以下の 8 ステップで、企画から動画完成までを自動実行します。

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
# レビューで却下されたショットを最大3回まで自動で作り直します。
python3 tools/regenerate_failed_shots.py \
  --project projects/exhibition_pr --max-rounds 3 --auto-review

# 7. ショット間の連続性適用 (オプション)
# 前のショットの最後を次の開始画像に設定します。
python3 tools/link_shots_continuity.py --project projects/exhibition_pr --force

# 8. Remotion タイムラインへの組み立てとレンダリング
python3 tools/build_remotion_timeline.py \
  --project projects/exhibition_pr --remotion-dir remotion
cd remotion
npm run build
```

## 高度な機能

### キャラクター & スタイル・バイブル
`projects/<project_dir>/` 内に `character_bible.json` または `style_bible.json` を配置すると、プランナーおよび T2I 生成時にその設定が自動的に反映されます。

### ワークフロー・プリセット
`workflow_presets/` 内の JSON で、ComfyUI のノード ID マッピングを管理します。独自のワークフローを使用する場合は、ここを編集してノードを紐付けてください。

## トラブルシューティング

### "missing_node_type" エラーが出る場合
ComfyUI の API ワークフロー JSON に、インストールされていないカスタムノードが含まれています。
1. ComfyUI でワークフローを開き、Group Node/Subgraph があれば展開（Ungroup）します。
2. 設定で **Dev Mode** を有効にし、**Save (API Format)** で保存し直してください。
3. 保存した JSON をプロジェクトの `comfy_workflows/` 内のものと差し替えます。

### ComfyUI が応答しない
`COMFYUI_URL` が正しいか、ComfyUI が起動しているか確認してください。
```bash
curl http://127.0.0.1:8188/system_stats
```

---

*このプロジェクトは、SusHi Tech Tokyo 2026 等の展示会における自律的な映像制作体験を提供するために開発されています。*
