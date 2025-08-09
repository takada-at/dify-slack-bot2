import json
import traceback
from collections.abc import Mapping

import requests
from dify_plugin import Endpoint
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from werkzeug import Request, Response


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
                files = event.get("files", []) if settings.get("enable_file_attachments") else []
                if message.startswith("<@"):
                    message = message.split("> ", 1)[1] if "> " in message else message
                    channel = event.get("channel", "")
                    blocks = event.get("blocks", [])
                    blocks[0]["elements"][0]["elements"] = (
                        blocks[0].get("elements")[0].get("elements")[1:]
                    )
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
                    reaction = event.get("reaction", "")

                    message = f":{reaction}:"
                    thread_ts = (
                        message_ts if settings.get("enable_thread_reply") else None
                    )

                    blocks = [
                        {"type": "section", "text": {"type": "mrkdwn", "text": message}}
                    ]
                    return self._process_dify_request(
                        message, channel, blocks, thread_ts, settings, []
                    )
                else:
                    return Response(status=200, response="ok")
            else:
                return Response(status=200, response="ok")
        else:
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
        token = settings.get("bot_token")
        client = WebClient(token=token)

        uploaded_files: list = []
        if files and settings.get("enable_file_attachments"):
            uploaded_files = self._upload_slack_files_to_dify(files, client)
            if uploaded_files:
                file_summary = f"\n\n添付ファイル: {', '.join([f.filename for f in uploaded_files])}"
                message += file_summary

        try:
            inputs = {}
            if uploaded_files:
                inputs["files"] = uploaded_files
            response = self.session.app.chat.invoke(
                app_id=settings["app"]["app_id"],
                query=message,
                inputs=inputs,
                response_mode="blocking",
            )
            try:
                if blocks and len(blocks) > 0 and "text" in blocks[0]:
                    blocks[0]["text"]["text"] = response.get("answer")
                elif blocks and len(blocks) > 0 and "elements" in blocks[0]:
                    blocks[0]["elements"][0]["elements"][0]["text"] = response.get(
                        "answer"
                    )

                post_message_args = {
                    "channel": channel,
                    "text": response.get("answer"),
                    "blocks": blocks,
                }
                if thread_ts:
                    post_message_args["thread_ts"] = thread_ts

                result = client.chat_postMessage(**post_message_args)
                return Response(
                    status=200,
                    response=json.dumps(result),
                    content_type="application/json",
                )
            except SlackApiError as e:
                raise e
        except Exception:
            err = traceback.format_exc()
            return Response(
                status=200,
                response="Sorry, I'm having trouble processing your request. Please try again later."
                + str(err),
                content_type="text/plain",
            )

    def _upload_slack_files_to_dify(self, files: list, client: WebClient) -> list:
        """Download files from Slack and upload them to Dify"""
        uploaded_files = []
        for file_info in files:
            try:
                file_id = file_info.get("id")
                if not file_id:
                    continue

                file_response = client.files_info(file=file_id)
                if file_response.get("ok"):
                    file_data_response: dict = file_response.get("file", {})
                    url_private = file_data_response.get("url_private")

                    if url_private:
                        headers = {"Authorization": f"Bearer {client.token}"}
                        response = requests.get(url_private, headers=headers)

                        if response.status_code == 200:
                            dify_file = self.session.file.upload(
                                filename=file_data_response.get("name", "unknown"),
                                content=response.content,
                                mimetype=file_data_response.get("mimetype", "application/octet-stream")
                            )
                            uploaded_files.append(dify_file)
            except Exception as e:
                print(f"Error processing file {file_info.get('id', 'unknown')}: {e}")
                continue

        return uploaded_files
