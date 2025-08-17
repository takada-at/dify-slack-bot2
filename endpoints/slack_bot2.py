import json
import logging
import traceback
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs, urlparse

from dify_plugin import Endpoint
from dify_plugin.config.logger_format import plugin_logger_handler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.slack_response import SlackResponse
from werkzeug import Request, Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(plugin_logger_handler)


class SlackBot2Endpoint(Endpoint):
    def _invoke(self, r: Request, values: Mapping, settings: Mapping) -> Response:
        """
        Invokes the endpoint with the given request.
        """
        retry_num = r.headers.get("X-Slack-Retry-Num")
        if not settings.get("allow_retry") and (
            r.headers.get("X-Slack-Retry-Reason") == "http_timeout"
            or (retry_num is not None and int(retry_num) > 0)
        ):
            return Response(status=200, response="ok")
        data = r.get_json()

        # Handle Slack URL verification challenge
        if data.get("type") == "url_verification":
            return Response(
                response=json.dumps({"challenge": data.get("challenge")}),
                status=200,
                content_type="application/json",
            )
        if data.get("type") == "event_callback":
            event = data.get("event")
            if event.get("type") == "app_mention":
                message = event.get("text", "")
                files = event.get("files", [])
                if message.startswith("<@"):
                    message = message.split("> ", 1)[1] if "> " in message else message
                    channel = event.get("channel", "")
                    blocks = event.get("blocks", [])
                    if (
                        isinstance(blocks, list)
                        and len(blocks) > 0
                        and isinstance(blocks[0], dict)
                        and "elements" in blocks[0]
                        and isinstance(blocks[0]["elements"], list)
                        and len(blocks[0]["elements"]) > 0
                        and isinstance(blocks[0]["elements"][0], dict)
                        and "elements" in blocks[0]["elements"][0]
                    ):
                        blocks[0]["elements"][0]["elements"] = []
                    message_ts = event.get("ts")
                    return self._process_dify_request(
                        message=message,
                        channel=channel,
                        blocks=blocks,
                        message_ts=message_ts,
                        settings=settings,
                        event_type="app_mention",
                        reaction=None,
                        files=files,
                    )
                else:
                    return Response(status=200, response="ok")
            elif event.get("type") == "reaction_added":
                target_reactions = settings.get("target_reactions", "")
                if target_reactions:
                    allowed_reactions = [
                        r.strip() for r in target_reactions.split(",") if r.strip()
                    ]
                    if event.get("reaction") not in allowed_reactions:
                        return Response(status=200, response="ok")

                item = event.get("item", {})
                if item.get("type") == "message":
                    channel = item.get("channel", "")
                    message_ts = item.get("ts", "")
                    return self._on_reaction(
                        channel, message_ts, settings, event.get("reaction")
                    )
                else:
                    return Response(status=200, response="ok")
            else:
                return Response(status=200, response="ok")
        else:
            return Response(status=200, response="ok")

    def _get_original(
        self, client: WebClient, channel: str, message_ts: str
    ) -> SlackResponse | None:
        """Fetch Original Message From Slack."""
        permalink_resp = client.chat_getPermalink(
            channel=channel, message_ts=message_ts
        )
        if not permalink_resp:
            return None
        permalink = permalink_resp["permalink"]
        parsed = urlparse(permalink)
        thread_ts = None
        if parsed.query:
            params = parse_qs(parsed.query)
            thread_ts_list = params.get("thread_ts")
            thread_ts = thread_ts_list[0] if thread_ts_list else None
        if thread_ts is None or message_ts == thread_ts:
            return client.conversations_history(
                channel=channel, oldest=message_ts, inclusive=True, limit=1
            )
        else:
            # thread message
            return client.conversations_replies(
                channel=channel,
                ts=message_ts,
                inclusive=True,
                limit=1,
            )

    def _on_reaction(
        self,
        channel: str,
        message_ts: str,
        settings: Mapping,
        reaction: str,
    ) -> Response:
        try:
            token = settings.get("bot_token")
            client = WebClient(token=token)
            response = self._get_original(
                client=client, channel=channel, message_ts=message_ts
            )
            if response and response.get("messages"):
                message = response["messages"][0]
                files = message.get("files", [])
                blocks = message.get("blocks", [])
                if (
                    isinstance(blocks, list)
                    and len(blocks) > 0
                    and isinstance(blocks[0], dict)
                    and "elements" in blocks[0]
                    and isinstance(blocks[0]["elements"], list)
                    and len(blocks[0]["elements"]) > 0
                    and isinstance(blocks[0]["elements"][0], dict)
                    and "elements" in blocks[0]["elements"][0]
                    and isinstance(blocks[0]["elements"][0]["elements"], list)
                ):
                    blocks[0]["elements"][0]["elements"] = []
                message_text = message.get("text", "")
                return self._process_dify_request(
                    message=message_text,
                    channel=channel,
                    blocks=blocks,
                    message_ts=message_ts,
                    settings=settings,
                    event_type="reaction_added",
                    reaction=reaction,
                    files=files,
                )
            return Response(status=200, response="ok")
        except SlackApiError as e:
            logger.error("Error fetching message: %s", e.response["error"])
            return Response(status=200, response="ok")
        except Exception as e:
            err = traceback.format_exc()
            logger.error("Error processing request: %s: %s", type(e).__name__, str(e))
            logger.error("Traceback: %s", err)
            return Response(status=200, response="ok")

    def _process_dify_request(
        self,
        message: str,
        channel: str,
        blocks: list,
        message_ts: str,
        settings: Mapping,
        event_type: str,
        reaction: str | None = None,
        files: list | None = None,
    ) -> Response:
        """Process request to Dify and post response to Slack"""
        try:
            enable_thread = settings.get("enable_thread_reply", False)
            token = settings.get("bot_token")
            client = WebClient(token=token)
            inputs: dict[str, Any] = {
                "channel": channel,
                "message_ts": message_ts,
                "event_type": event_type,
                "reaction": reaction,
            }
            response = self.session.app.chat.invoke(
                app_id=settings["app"]["app_id"],
                query=message,
                inputs=inputs,
                response_mode="blocking",
            )
            if blocks and len(blocks) > 0 and "text" in blocks[0]:
                blocks[0]["text"]["text"] = response.get("answer")
            elif blocks and len(blocks) > 0 and "elements" in blocks[0]:
                element = {"type": "text", "text": response.get("answer")}
                blocks[0]["elements"][0]["elements"].append(element)
            post_message_args = {
                "channel": channel,
                "text": response.get("answer"),
                "blocks": blocks,
            }
            if enable_thread:
                post_message_args["thread_ts"] = message_ts

            client.chat_postMessage(**post_message_args)
            return Response(
                status=200,
                response="ok",
                content_type="application/json",
            )
        except Exception as e:
            err = traceback.format_exc()
            logger.error("Error processing request: %s: %s", type(e).__name__, str(e))
            logger.error("Traceback: %s", err)
            return Response(
                status=200,
                response="ok",
                content_type="text/plain",
            )
