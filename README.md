# Dify Slack Bot Plugin (slack-bot2)

Also available in Japanese: README.ja.md

## Overview
This repository contains an Extension-type Dify plugin that connects Slack to a Dify application. The plugin listens to Slack events (app mentions and optionally reaction_added), invokes a configured Dify app, and posts the result back to Slack (optionally in a thread).

- Entry point: main.py
- Core endpoint: endpoints/slack-bot2.py (SlackBot2Endpoint)
- Settings schema: group/slack-bot2.yaml
- Plugin manifest: manifest.yaml
- Tests: tests/test_slack_bot2_endpoint.py
- Detailed setup guide: docs/plugin-setup-guide.md

## Features
- App mentions: Responds when users mention the bot in Slack (@bot)
- Reaction trigger: Optionally triggers on specified emoji reactions (reaction_added)
- Thread replies: Optionally reply in the original message thread
- Retry control: Configure whether to process Slack retry requests
- Error handling: Acknowledge Slack events and surface meaningful errors

## Requirements
- Python 3.12
- Dify Plugin SDK (dify_plugin)
- Slack SDK (slack_sdk)
- A Slack App with proper scopes and event subscriptions
- Access to a Dify instance and a Dify app to invoke

## Quick Setup
For full, step-by-step instructions, see docs/plugin-setup-guide.md. Below is a concise summary.

1) Create a Slack App
- Add Bot Token scopes (OAuth & Permissions):
  - app_mentions:read
  - chat:write
  - reactions:read (if using reaction triggers)
- Enable Event Subscriptions and set Request URL to the plugin endpoint:
  - https://YOUR-DIFY-ENDPOINT/plugins/endpoints/uwu/slack-bot2/uwu
- Subscribe to bot events:
  - app_mention
  - reaction_added (optional)
- Install the app to your workspace and obtain the Bot User OAuth Token (xoxb-*)

2) Configure the Plugin in Dify
- Set bot_token with the Slack Bot User OAuth Token (xoxb-*)
- Choose the Dify app to invoke for Slack messages
- Optional settings:
  - allow_retry: whether to process Slack retries (default: false)
  - target_reactions: comma-separated emoji names for reaction triggers
  - enable_thread_reply: post replies in threads when true

## Local Debugging
You can connect a local plugin process to a Dify instance for debugging.

1) Create a .env in the project root:
- INSTALL_METHOD=remote
- REMOTE_INSTALL_URL=debug.dify.ai
- REMOTE_INSTALL_PORT=5003
- REMOTE_INSTALL_KEY=YOUR_DEBUG_KEY

2) Run the plugin:
- python -m main

Refresh the Dify UI; the plugin appears as debugging and can be used for tests.

## Verification (Manual)
- Mention: In a channel with the bot, mention it (e.g., @your-bot-name hello) and verify it replies.
- Reaction: If configured, add a target emoji to a message and verify the bot responds.
- Thread: If enabled, verify the response posts in the message thread.

See docs/plugin-setup-guide.md for detailed troubleshooting steps.

## Development
Install dependencies:
- pip install -r requirements.txt
- pip install -r requirements-dev.txt

Quality and tests:
- ruff check .
- mypy .
- pytest

## Project Structure
- main.py: Initializes and runs the plugin with a 120s timeout
- endpoints/slack-bot2.py: SlackBot2Endpoint handling Slack events and Dify integration
- endpoints/slack-bot2.yaml: Endpoint route definition
- group/slack-bot2.yaml: User-configurable settings schema
- manifest.yaml: Plugin metadata and configuration
- tests/test_slack_bot2_endpoint.py: Unit tests
- docs/plugin-setup-guide.md: Detailed setup and configuration guide
- GUIDE.md, CLAUDE.md: Additional development guidance
- PRIVACY.md: Privacy policy template

## License and Author
- Author: takada-at
- Version: 0.0.1
- Type: extension
