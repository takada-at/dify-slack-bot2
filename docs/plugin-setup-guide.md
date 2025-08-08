# Dify Slack Bot プラグイン設定ガイド

このガイドでは、Dify Slack Bot プラグインの設定方法について詳しく説明します。

## 概要

このプラグインは、SlackとDifyを連携させるExtension型プラグインです。Slackでのメンション（@bot）やリアクション追加イベントを受信し、指定したDifyアプリを呼び出して、結果をSlackに投稿します。

## 主な機能

- **メンション対応**: Slackでボットにメンションすると、Difyアプリが応答します
- **リアクション対応**: 指定したリアクションが追加されると、Difyアプリが起動します
- **スレッド返信**: 元メッセージのスレッドに返信する機能
- **再試行制御**: Slackからの再試行リクエストを制御する機能

## 事前準備

### 1. Slack App の作成

1. [Slack API](https://api.slack.com/apps) にアクセス
2. 「Create New App」をクリック
3. 「From scratch」を選択
4. アプリ名とワークスペースを設定

### 2. Slack App の設定

#### Bot Token Scopes の設定
「OAuth & Permissions」ページで以下のスコープを追加：

- `app_mentions:read` - メンションイベントの読み取り
- `chat:write` - メッセージの投稿
- `reactions:read` - リアクションイベントの読み取り

#### Event Subscriptions の設定
「Event Subscriptions」ページで：

1. 「Enable Events」をオンにする
2. 「Request URL」にプラグインのエンドポイントURLを設定
   - 形式: `https://your-dify-instance.com/plugins/endpoints/uwu/slack-bot2/uwu`
3. 「Subscribe to bot events」で以下のイベントを追加：
   - `app_mention` - ボットへのメンション
   - `reaction_added` - リアクション追加（オプション）

#### Bot Token の取得
「OAuth & Permissions」ページで「Install to Workspace」をクリックし、Bot User OAuth Tokenを取得します。

## プラグイン設定

### 1. 基本設定

#### Bot Token
- **必須項目**
- Slack App から取得したBot User OAuth Token（`xoxb-`で始まる）を入力
- セキュアな入力フィールドで、値は暗号化されて保存されます

#### App（アプリ選択）
- **必須項目**
- Slackメッセージに応答するために使用するDifyアプリを選択
- ドロップダウンから利用可能なアプリを選択できます

### 2. 詳細設定

#### Allow Retry（再試行を許可）
- **オプション項目**（デフォルト: false）
- Slackからの再試行リクエストを許可するかどうか
- `false`の場合、タイムアウトや重複リクエストを自動的に無視します

#### Target Reactions（対象リアクション）
- **オプション項目**
- リアクション追加イベントで反応するリアクション名をカンマ区切りで指定
- 例: `thumbsup,heart,fire`
- 空の場合、すべてのリアクションに反応します

#### Enable Thread Reply（スレッド返信を有効にする）
- **オプション項目**（デフォルト: false）
- `true`の場合、元メッセージのスレッドに返信します
- `false`の場合、チャンネルに新しいメッセージとして投稿します

## デバッグ環境の設定

ローカルでプラグインをテストする場合は、以下の環境変数を設定します。

### .env ファイルの作成

プロジェクトルートに `.env` ファイルを作成し、以下の内容を設定：

```env
INSTALL_METHOD=remote
REMOTE_INSTALL_URL=debug.dify.ai
REMOTE_INSTALL_PORT=5003
REMOTE_INSTALL_KEY=your-debug-key-here
```

### 環境変数の説明

- `INSTALL_METHOD`: `remote` に設定（ネットワーク経由でDifyインスタンスに接続）
- `REMOTE_INSTALL_URL`: DifyインスタンスのデバッグホストURL
- `REMOTE_INSTALL_PORT`: プラグインデーモンサービスのポート（通常5003）
- `REMOTE_INSTALL_KEY`: Difyインスタンスから取得したデバッグキー

### デバッグキーの取得方法

1. Difyインスタンスのプラグイン管理ページにアクセス
2. 右上の「debug」アイコンをクリック
3. 表示されたキーをコピーして `REMOTE_INSTALL_KEY` に設定

### ローカル実行

```bash
python -m main
```

実行後、Difyインスタンスのページを更新すると、プラグインが「debugging」状態で表示されます。

## 動作確認

### 1. メンション機能のテスト

1. Slackでボットが追加されたチャンネルに移動
2. `@your-bot-name こんにちは` のようにメンション
3. Difyアプリからの応答が返ってくることを確認

### 2. リアクション機能のテスト（設定している場合）

1. 任意のメッセージに設定したリアクションを追加
2. Difyアプリが起動し、応答が投稿されることを確認

### 3. スレッド返信のテスト（有効にしている場合）

1. メンションまたはリアクションでボットを起動
2. 応答が元メッセージのスレッドに投稿されることを確認

## トラブルシューティング

### よくある問題と解決方法

#### 1. ボットが応答しない

**確認項目:**
- Bot Tokenが正しく設定されているか
- Slack AppのEvent SubscriptionsでRequest URLが正しく設定されているか
- 必要なBot Token Scopesが追加されているか
- 選択したDifyアプリが正常に動作するか

**解決方法:**
- Slack APIのEvent Subscriptionsページでエンドポイントの検証状況を確認
- Difyのログでエラーメッセージを確認
- プラグインのデバッグモードで動作を確認

#### 2. リアクション機能が動作しない

**確認項目:**
- `reactions:read` スコープが追加されているか
- Event Subscriptionsで `reaction_added` イベントが登録されているか
- Target Reactionsの設定が正しいか

**解決方法:**
- Slack AppのOAuth & Permissionsでスコープを確認
- Target Reactionsの値を確認（カンマ区切り、スペースなし）

#### 3. 重複した応答が投稿される

**確認項目:**
- Allow Retryの設定を確認

**解決方法:**
- Allow Retryを `false` に設定（推奨）
- Slackの再試行メカニズムによる重複を防ぐ

#### 4. スレッド返信が機能しない

**確認項目:**
- Enable Thread Replyが `true` に設定されているか
- Slackのメッセージ構造が正しく処理されているか

**解決方法:**
- 設定を確認し、必要に応じて再設定
- 異なるメッセージタイプでテスト

### ログの確認方法

デバッグモードでプラグインを実行している場合：

1. コンソール出力でエラーメッセージを確認
2. Difyインスタンスのログを確認
3. Slack APIのEvent Subscriptionsページでリクエスト履歴を確認

### サポート

問題が解決しない場合は、以下の情報を含めてサポートに連絡してください：

- プラグインのバージョン
- Difyのバージョン
- エラーメッセージ
- 設定内容（機密情報は除く）
- 再現手順

## 参考資料

- [Dify プラグイン開発ガイド](./dify-plugin-document.md)
- [Extension型プラグインドキュメント](./dify-extension-plugin-document.md)
- [Slack Events API](./slack-events-api.md)
- [Slack API ドキュメント](https://api.slack.com/)

---

**作成者:** takada-at  
**バージョン:** 0.0.1  
**最終更新:** 2025年8月8日
