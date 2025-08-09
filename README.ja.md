# Dify Slack Bot プラグイン (slack-bot2)

英語版のREADME: README.md

## 概要
Slack と Dify アプリを連携する Extension 型プラグインです。Slack のイベント（ボットへのメンション、および任意で reaction_added）を受け取り、設定した Dify アプリを呼び出して、結果を Slack に（任意でスレッドに）投稿します。

- エントリーポイント: main.py
- 中核エンドポイント: endpoints/slack-bot2.py（SlackBot2Endpoint）
- 設定スキーマ: group/slack-bot2.yaml
- プラグイン定義: manifest.yaml
- テスト: tests/test_slack_bot2_endpoint.py
- 詳細セットアップガイド: docs/plugin-setup-guide.md

## 主な機能
- メンション対応: Slack でボットにメンションされると応答
- リアクション対応: 指定した絵文字リアクション（reaction_added）で起動（任意）
- スレッド返信: 元メッセージのスレッドに返信可能（任意）
- 再試行制御: Slack のリトライリクエスト処理の可否を設定可能
- エラーハンドリング: Slack イベントの即時 ACK と分かりやすいエラー返却

## 必要条件
- Python 3.12
- Dify Plugin SDK（dify_plugin）
- Slack SDK（slack_sdk）
- 適切なスコープとイベントサブスクリプションを持つ Slack App
- Dify インスタンス、および呼び出す対象の Dify アプリ

## かんたんセットアップ
詳細な手順は docs/plugin-setup-guide.md を参照してください。以下はダイジェストです。

1) Slack App の作成・設定
- Bot Token Scopes（OAuth & Permissions）に以下を追加
  - app_mentions:read
  - chat:write
  - reactions:read（リアクショントリガーを使う場合）
- Event Subscriptions を有効化し、Request URL をプラグインのエンドポイントに設定
  - https://YOUR-DIFY-ENDPOINT/plugins/endpoints/uwu/slack-bot2/uwu
- Subscribe to bot events に以下を追加
  - app_mention
  - reaction_added（任意）
- ワークスペースにインストールし、Bot User OAuth Token（xoxb- で始まる）を取得

2) Dify 側でプラグイン設定
- bot_token: Slack の Bot User OAuth Token（xoxb-）を設定（必須）
- app: 応答に使用する Dify アプリを選択（必須）
- オプション設定
  - allow_retry: Slack の再試行リクエストを処理するか（デフォルト: false）
  - target_reactions: リアクション名をカンマ区切りで指定
  - enable_thread_reply: true の場合、スレッドに返信

## ローカルデバッグ
ローカルプロセスを Dify に接続してデバッグできます。

1) プロジェクト直下に .env を作成
- INSTALL_METHOD=remote
- REMOTE_INSTALL_URL=debug.dify.ai
- REMOTE_INSTALL_PORT=5003
- REMOTE_INSTALL_KEY=YOUR_DEBUG_KEY

2) プラグインを起動
- python -m main

Dify の画面を更新すると、プラグインが debugging 状態で表示されます。

## 動作確認（手動）
- メンション: ボットがいるチャンネルで @your-bot-name こんにちは などとメンションし、応答を確認
- リアクション: 設定していれば、対象の絵文字を任意メッセージに追加して応答を確認
- スレッド: enable_thread_reply が true の場合、スレッドに返信されることを確認

詳細なトラブルシューティングは docs/plugin-setup-guide.md を参照してください。

## 開発
依存関係のインストール
- pip install -r requirements.txt
- pip install -r requirements-dev.txt

品質とテスト
- ruff check .
- mypy .
- pytest

## プロジェクト構成
- main.py: プラグイン起動（タイムアウト 120 秒）
- endpoints/slack-bot2.py: Slack イベント処理と Dify 連携
- endpoints/slack-bot2.yaml: エンドポイントのルート定義
- group/slack-bot2.yaml: ユーザー設定スキーマ
- manifest.yaml: プラグインメタデータ
- tests/test_slack_bot2_endpoint.py: ユニットテスト
- docs/plugin-setup-guide.md: 詳細セットアップガイド
- GUIDE.md, CLAUDE.md: 開発の補助資料
- PRIVACY.md: プライバシーポリシー

## ライセンス・作者情報
- Author: takada-at
- Version: 0.0.1
- Type: extension
