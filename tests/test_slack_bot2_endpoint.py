import importlib.util
import json
import os
import sys
from typing import Any
from unittest.mock import Mock, patch

import pytest
from slack_sdk.errors import SlackApiError
from werkzeug import Request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location(
    "slack_bot2",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "endpoints",
        "slack-bot2.py",
    ),
)
if spec is None or spec.loader is None:
    raise ImportError("Could not load slack-bot2.py module")
slack_bot2_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slack_bot2_module)
SlackBot2Endpoint = slack_bot2_module.SlackBot2Endpoint


class TestSlackBot2Endpoint:
    @pytest.fixture
    def endpoint(self) -> Any:
        mock_session = Mock()
        mock_session.app = Mock()
        mock_session.app.chat = Mock()
        endpoint = SlackBot2Endpoint(mock_session)
        return endpoint

    @pytest.fixture
    def mock_request(self) -> Mock:
        request = Mock(spec=Request)
        request.headers = {}
        return request

    @pytest.fixture
    def basic_settings(self) -> dict[str, Any]:
        return {
            "bot_token": "xoxb-test-token",
            "app": {"app_id": "test-app-id"},
            "allow_retry": False,
            "enable_thread_reply": False,
            "target_reactions": "",
        }

    @pytest.fixture
    def url_verification_data(self) -> dict[str, Any]:
        return {"type": "url_verification", "challenge": "test-challenge-string"}

    @pytest.fixture
    def app_mention_data(self) -> dict[str, Any]:
        return {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "<@U123456> Hello bot!",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "blocks": [
                    {
                        "elements": [
                            {
                                "elements": [
                                    {"text": "<@U123456>"},
                                    {"text": " Hello bot!"},
                                ]
                            }
                        ]
                    }
                ],
            },
        }

    @pytest.fixture
    def reaction_added_data(self) -> dict[str, Any]:
        return {
            "type": "event_callback",
            "event": {
                "type": "reaction_added",
                "reaction": "thumbsup",
                "item": {
                    "type": "message",
                    "channel": "C123456",
                    "ts": "1234567890.123456",
                },
            },
        }

    def test_invoke_url_verification_challenge(
        self,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        url_verification_data: Any,
    ) -> None:
        mock_request.get_json.return_value = url_verification_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        assert response.content_type == "application/json"
        response_data = json.loads(response.get_data(as_text=True))
        assert response_data["challenge"] == "test-challenge-string"

    def test_invoke_retry_blocked_when_retry_not_allowed(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        basic_settings["allow_retry"] = False
        mock_request.headers = {"X-Slack-Retry-Reason": "http_timeout"}
        mock_request.get_json.return_value = {"type": "event_callback"}

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        assert response.get_data(as_text=True) == "ok"

    def test_invoke_retry_blocked_with_retry_num(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        basic_settings["allow_retry"] = False
        mock_request.headers = {"X-Slack-Retry-Num": "1"}
        mock_request.get_json.return_value = {"type": "event_callback"}

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        assert response.get_data(as_text=True) == "ok"

    def test_invoke_retry_allowed_when_enabled(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        basic_settings["allow_retry"] = True
        mock_request.headers = {"X-Slack-Retry-Reason": "http_timeout"}
        mock_request.get_json.return_value = {
            "type": "event_callback",
            "event": {"type": "unknown"},
        }

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200

    @patch.object(slack_bot2_module, "WebClient")
    def test_invoke_app_mention_success(
        self,
        mock_webclient_class: Any,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        app_mention_data: Any,
    ) -> None:
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }

        endpoint.session.app.chat.invoke.return_value = {
            "answer": "Hello! How can I help you?"
        }
        mock_request.get_json.return_value = app_mention_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        endpoint.session.app.chat.invoke.assert_called_once_with(
            app_id="test-app-id",
            query="Hello bot!",
            inputs={},
            response_mode="blocking",
        )
        mock_webclient.chat_postMessage.assert_called_once()

    def test_invoke_app_mention_without_mention_prefix(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        data = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "Hello bot!",
                "channel": "C123456",
            },
        }
        mock_request.get_json.return_value = data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        assert response.get_data(as_text=True) == "ok"

    @patch.object(slack_bot2_module, "WebClient")
    def test_invoke_app_mention_with_thread_reply(
        self,
        mock_webclient_class: Any,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        app_mention_data: Any,
    ) -> None:
        basic_settings["enable_thread_reply"] = True
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {"answer": "Thread reply"}
        mock_request.get_json.return_value = app_mention_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        call_args = mock_webclient.chat_postMessage.call_args[1]
        assert "thread_ts" in call_args
        assert call_args["thread_ts"] == "1234567890.123456"

    @patch.object(slack_bot2_module, "WebClient")
    def test_invoke_reaction_added_success(
        self,
        mock_webclient_class: Any,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        reaction_added_data: Any,
    ) -> None:
        basic_settings["target_reactions"] = "thumbsup,heart"
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {"answer": "Reaction response"}
        mock_request.get_json.return_value = reaction_added_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        endpoint.session.app.chat.invoke.assert_called_once_with(
            app_id="test-app-id",
            query=":thumbsup:",
            inputs={},
            response_mode="blocking",
        )

    def test_invoke_reaction_added_not_in_target_reactions(
        self,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        reaction_added_data: Any,
    ) -> None:
        basic_settings["target_reactions"] = "heart,fire"
        mock_request.get_json.return_value = reaction_added_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        assert response.get_data(as_text=True) == "ok"

    def test_invoke_reaction_added_no_target_reactions_configured(
        self,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        reaction_added_data: Any,
    ) -> None:
        basic_settings["target_reactions"] = ""
        mock_request.get_json.return_value = reaction_added_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200

    def test_invoke_reaction_added_non_message_item(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        data = {
            "type": "event_callback",
            "event": {
                "type": "reaction_added",
                "reaction": "thumbsup",
                "item": {"type": "file", "file": "F123456"},
            },
        }
        mock_request.get_json.return_value = data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        assert response.get_data(as_text=True) == "ok"

    def test_invoke_unknown_event_type(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        data = {"type": "event_callback", "event": {"type": "unknown_event"}}
        mock_request.get_json.return_value = data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        assert response.get_data(as_text=True) == "ok"

    def test_invoke_unknown_callback_type(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        data = {"type": "unknown_type"}
        mock_request.get_json.return_value = data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        assert response.get_data(as_text=True) == "ok"

    @patch.object(slack_bot2_module, "WebClient")
    def test_process_dify_request_success(
        self, mock_webclient_class: Any, endpoint: Any, basic_settings: Any
    ) -> None:
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }

        endpoint.session.app.chat.invoke.return_value = {"answer": "Test response"}

        blocks = [{"text": {"text": "original"}}]
        response = endpoint._process_dify_request(
            "test message", "C123456", blocks, None, basic_settings
        )

        assert response.status_code == 200
        mock_webclient.chat_postMessage.assert_called_once()
        call_args = mock_webclient.chat_postMessage.call_args[1]
        assert call_args["channel"] == "C123456"
        assert call_args["text"] == "Test response"
        assert "thread_ts" not in call_args

    @patch.object(slack_bot2_module, "WebClient")
    def test_process_dify_request_with_thread_ts(
        self, mock_webclient_class: Any, endpoint: Any, basic_settings: Any
    ) -> None:
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {"answer": "Thread response"}

        blocks = [{"text": {"text": "original"}}]
        endpoint._process_dify_request(
            "test", "C123456", blocks, "1234567890.123456", basic_settings, []
        )

        call_args = mock_webclient.chat_postMessage.call_args[1]
        assert call_args["thread_ts"] == "1234567890.123456"

    @patch.object(slack_bot2_module, "WebClient")
    def test_process_dify_request_with_elements_blocks(
        self, mock_webclient_class: Any, endpoint: Any, basic_settings: Any
    ) -> None:
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {"answer": "Elements response"}

        blocks = [{"elements": [{"elements": [{"text": "original"}]}]}]
        response = endpoint._process_dify_request(
            "test", "C123456", blocks, None, basic_settings, []
        )

        assert response.status_code == 200
        assert blocks[0]["elements"][0]["elements"][0]["text"] == "Elements response"

    @patch.object(slack_bot2_module, "WebClient")
    def test_process_dify_request_slack_api_error(
        self, mock_webclient_class: Any, endpoint: Any, basic_settings: Any
    ) -> None:
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.side_effect = SlackApiError(
            "API Error", response={"error": "channel_not_found"}
        )

        endpoint.session.app.chat.invoke.return_value = {"answer": "Test response"}

        response = endpoint._process_dify_request(
            "test", "C123456", [], None, basic_settings, []
        )
        assert response.status_code == 200

    @patch.object(slack_bot2_module, "WebClient")
    def test_process_dify_request_general_exception(
        self, mock_webclient_class: Any, endpoint: Any, basic_settings: Any
    ) -> None:
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient

        endpoint.session.app.chat.invoke.side_effect = Exception("Dify API Error")

        response = endpoint._process_dify_request(
            "test", "C123456", [], None, basic_settings, []
        )

        assert response.status_code == 200
        assert response.content_type == "text/plain"
        response_text = response.get_data(as_text=True)
        assert "Sorry, I'm having trouble processing your request" in response_text
        assert "Dify API Error" in response_text

    @patch.object(slack_bot2_module, "WebClient")
    def test_process_dify_request_empty_blocks(
        self, mock_webclient_class: Any, endpoint: Any, basic_settings: Any
    ) -> None:
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {
            "answer": "Empty blocks response"
        }

        response = endpoint._process_dify_request(
            "test", "C123456", [], None, basic_settings, []
        )

        assert response.status_code == 200
        call_args = mock_webclient.chat_postMessage.call_args[1]
        assert call_args["blocks"] == []

    def test_invoke_malformed_json(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        mock_request.get_json.side_effect = Exception("Invalid JSON")

        with pytest.raises(Exception, match="Invalid JSON"):
            endpoint._invoke(mock_request, {}, basic_settings)

    @patch.object(slack_bot2_module, "WebClient")
    def test_invoke_app_mention_missing_blocks(
        self,
        mock_webclient_class: Any,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
    ) -> None:
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {"answer": "Response"}

        data = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "<@U123456> Hello",
                "channel": "C123456",
                "ts": "1234567890.123456",
            },
        }
        mock_request.get_json.return_value = data

        with pytest.raises(IndexError):
            endpoint._invoke(mock_request, {}, basic_settings)

    def test_invoke_app_mention_missing_channel(
        self, endpoint: Any, mock_request: Any, basic_settings: Any
    ) -> None:
        data = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "<@U123456> Hello",
                "ts": "1234567890.123456",
                "blocks": [
                    {
                        "elements": [
                            {"elements": [{"text": "<@U123456>"}, {"text": " Hello"}]}
                        ]
                    }
                ],
            },
        }
        mock_request.get_json.return_value = data

        with patch.object(slack_bot2_module, "WebClient") as mock_webclient_class:
            mock_webclient = Mock()
            mock_webclient_class.return_value = mock_webclient
            mock_webclient.chat_postMessage.return_value = {"ok": True}
            endpoint.session.app.chat.invoke.return_value = {"answer": "Response"}

            response = endpoint._invoke(mock_request, {}, basic_settings)

            assert response.status_code == 200
            call_args = mock_webclient.chat_postMessage.call_args[1]
            assert call_args["channel"] == ""

    @pytest.fixture
    def app_mention_with_files_data(self) -> dict[str, Any]:
        return {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "<@U123456> Please analyze this file",
                "channel": "C123456",
                "ts": "1234567890.123456",
                "files": [
                    {
                        "id": "F123456789",
                        "name": "test.txt",
                        "mimetype": "text/plain",
                        "size": 100
                    }
                ],
                "blocks": [
                    {
                        "elements": [
                            {
                                "elements": [
                                    {"text": "<@U123456>"},
                                    {"text": " Please analyze this file"},
                                ]
                            }
                        ]
                    }
                ],
            },
        }

    @patch.object(slack_bot2_module, "WebClient")
    @patch("requests.get")
    def test_invoke_app_mention_with_files_enabled(
        self,
        mock_requests_get: Any,
        mock_webclient_class: Any,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        app_mention_with_files_data: Any,
    ) -> None:
        basic_settings["enable_file_attachments"] = True
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.token = "xoxb-test-token"
        mock_webclient.files_info.return_value = {
            "ok": True,
            "file": {
                "id": "F123456789",
                "name": "test.txt",
                "url_private": "https://files.slack.com/test.txt",
                "mimetype": "text/plain",
                "size": 100
            }
        }
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.content = b"test file content"
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {"answer": "File analyzed"}
        mock_request.get_json.return_value = app_mention_with_files_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        endpoint.session.app.chat.invoke.assert_called_once()
        call_args = endpoint.session.app.chat.invoke.call_args[1]
        assert "files" in call_args["inputs"]
        assert len(call_args["inputs"]["files"]) == 1
        assert call_args["inputs"]["files"][0]["name"] == "test.txt"

    @patch.object(slack_bot2_module, "WebClient")
    def test_invoke_app_mention_with_files_disabled(
        self,
        mock_webclient_class: Any,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        app_mention_with_files_data: Any,
    ) -> None:
        basic_settings["enable_file_attachments"] = False
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {"answer": "Response without files"}
        mock_request.get_json.return_value = app_mention_with_files_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        endpoint.session.app.chat.invoke.assert_called_once()
        call_args = endpoint.session.app.chat.invoke.call_args[1]
        assert call_args["inputs"] == {}

    @patch.object(slack_bot2_module, "WebClient")
    @patch("requests.get")
    def test_download_slack_files_error_handling(
        self,
        mock_requests_get: Any,
        mock_webclient_class: Any,
        endpoint: Any,
        mock_request: Any,
        basic_settings: Any,
        app_mention_with_files_data: Any,
    ) -> None:
        basic_settings["enable_file_attachments"] = True
        mock_webclient = Mock()
        mock_webclient_class.return_value = mock_webclient
        mock_webclient.token = "xoxb-test-token"
        mock_webclient.files_info.return_value = {
            "ok": True,
            "file": {
                "id": "F123456789",
                "name": "test.txt",
                "url_private": "https://files.slack.com/test.txt",
                "mimetype": "text/plain",
                "size": 100
            }
        }
        mock_requests_get.return_value.status_code = 404
        mock_webclient.chat_postMessage.return_value = {"ok": True}

        endpoint.session.app.chat.invoke.return_value = {"answer": "Response"}
        mock_request.get_json.return_value = app_mention_with_files_data

        response = endpoint._invoke(mock_request, {}, basic_settings)

        assert response.status_code == 200
        endpoint.session.app.chat.invoke.assert_called_once()
        call_args = endpoint.session.app.chat.invoke.call_args[1]
        assert call_args["inputs"] == {}
