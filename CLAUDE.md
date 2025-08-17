# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Dify extension plugin for Slack bot integration. It enables Slack workspaces to interact with Dify applications through Slack events (app mentions and reactions).

### Key Technologies
- **Language**: Python 3.12
- **Framework**: Dify Plugin SDK (dify_plugin)
- **Integration**: Slack SDK (slack_sdk)
- **Type**: Extension plugin for Dify platform

## Common Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_slack_bot2_endpoint.py

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Run linter (ruff)
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Format code
ruff format .

# Type checking with mypy
mypy endpoints/ tests/
```

### Dependencies
```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

## Architecture Overview

### Plugin Structure
The plugin follows Dify's extension plugin architecture:

1. **Entry Point**: `main.py` - Initializes and runs the Dify plugin with a 120-second timeout
2. **Core Endpoint**: `endpoints/slack-bot2.py:SlackBot2Endpoint` - Handles all Slack event processing
3. **Configuration**: 
   - `manifest.yaml` - Plugin metadata and resource configuration
   - `group/slack-bot2.yaml` - Settings schema and endpoint registration
   - `endpoints/slack_bot2.yaml` - Endpoint path configuration

### Event Processing Flow
1. Slack sends events to the endpoint (`/uwu/slack-bot2/uwu`)
2. `SlackBot2Endpoint._invoke()` processes the request:
   - Handles URL verification challenges
   - Filters retry attempts based on settings
   - Routes events (app_mention, reaction_added) to appropriate handlers
3. `_process_dify_request()` interacts with Dify:
   - Invokes the configured Dify app with the message
   - Posts the response back to Slack (optionally in threads)

### Key Features
- **App Mentions**: Responds when the bot is mentioned in Slack
- **Reaction Handling**: Triggers Dify app when specific reactions are added (configurable via `target_reactions`)
- **Thread Replies**: Optional thread-based responses (controlled by `enable_thread_reply`)
- **Retry Management**: Configurable handling of Slack retry attempts

### Configuration Settings
Managed through `group/slack-bot2.yaml`:
- `bot_token`: Slack Bot User OAuth Token (required)
- `app`: Dify application selector (required)
- `allow_retry`: Enable/disable processing of Slack retries
- `target_reactions`: Comma-separated list of reactions to respond to
- `enable_thread_reply`: Post responses in threads vs. main channel

## Important Implementation Notes

1. **Slack Event Handling**: The endpoint must respond quickly (within 3 seconds) to avoid Slack retries. Current timeout is set to 120 seconds in `main.py`.

2. **Message Processing**: App mentions strip the bot mention prefix before sending to Dify. The message blocks are also modified to remove the mention element.

3. **Error Handling**: Exceptions during Dify processing return a user-friendly error message while still responding with HTTP 200 to acknowledge the Slack event.

4. **Testing**: Test file `tests/test_slack_bot2_endpoint.py` covers various Slack event scenarios including URL verification, app mentions, and reaction events.