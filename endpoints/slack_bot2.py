import json
import logging
import traceback
from collections.abc import Mapping
from typing import Any

from dify_plugin import Endpoint
from dify_plugin.config.logger_format import plugin_logger_handler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
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
                files = (
                    event.get("files", [])
                    if settings.get("enable_file_attachments")
                    else []
                )
                if message.startswith("<@"):
                    message = message.split("> ", 1)[1] if "> " in message else message
                    channel = event.get("channel", "")
                    blocks = event.get("blocks", [])
                    blocks[0]["elements"][0]["elements"] = []
                    thread_ts = (
                        event.get("ts") if settings.get("enable_thread_reply") else None
                    )
                    return self._process_dify_request(
                        message, channel, blocks, thread_ts, settings, files
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
                    thread_ts = (
                        message_ts if settings.get("enable_thread_reply") else None
                    )
                    return self._on_reaction(channel, message_ts, thread_ts, settings)
                else:
                    return Response(status=200, response="ok")
            else:
                return Response(status=200, response="ok")
        else:
            return Response(status=200, response="ok")

    def _on_reaction(
        self,
        channel: str,
        message_ts: str,
        thread_ts: str | None,
        settings: Mapping,
    ) -> Response:
        try:
            token = settings.get("bot_token")
            client = WebClient(token=token)
            response = client.conversations_history(
                channel=channel, latest=message_ts, limit=1, inclusive=True
            )
            if response and response.get("messages"):
                message = response["messages"][0]
                files = (
                    message.get("files", [])
                    if settings.get("enable_file_attachments")
                    else []
                )
                blocks = message.get("blocks", [])
                blocks[0]["elements"][0]["elements"] = []
                message_text = message.get("text", "")
                return self._process_dify_request(
                    message_text, channel, blocks, thread_ts, settings, files
                )
            return Response(status=200, response="ok")
        except SlackApiError as e:
            logger.error("Error fetching message: %s", e.response["error"])
            return Response(status=200, response="ok")

    def _process_dify_request(
        self,
        message: str,
        channel: str,
        blocks: list,
        thread_ts: str | None,
        settings: Mapping,
        files: list | None = None,
    ) -> Response:
        """Process request to Dify and post response to Slack"""
        try:
            token = settings.get("bot_token")
            client = WebClient(token=token)
            inputs: dict[str, Any] = {}
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
            if thread_ts:
                post_message_args["thread_ts"] = thread_ts

            client.chat_postMessage(**post_message_args)
            return Response(
                status=200,
                response="ok",
                content_type="application/json",
            )
        except Exception:
            err = traceback.format_exc()
            logger.error("Error processing request: %s", err)
            return Response(
                status=200,
                response="ok",
                content_type="text/plain",
            )
