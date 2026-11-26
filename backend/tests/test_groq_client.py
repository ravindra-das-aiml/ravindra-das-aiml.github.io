import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import SecretStr

from app.schemas.chat import ChatMessage
from app.services.groq_client import (
    GROQ_API_BASE_URL,
    _format_provider_error_body,
    generate_reply,
)


class GroqClientTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.groq_client.get_settings")
    @patch("app.services.groq_client.AsyncGroq")
    async def test_uses_official_api_root_and_supported_model(
        self, groq_client_factory, get_settings
    ):
        get_settings.return_value = SimpleNamespace(
            groq_api_key=SecretStr("test-key"),
            groq_model="openai/gpt-oss-120b",
            groq_timeout_seconds=25,
        )
        client = groq_client_factory.return_value
        client.chat.completions.create = AsyncMock(
            return_value=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="Portfolio answer")
                    )
                ]
            )
        )
        client.close = AsyncMock()

        reply = await generate_reply(
            [ChatMessage(role="user", content="Tell me about the projects.")]
        )

        self.assertEqual(reply, "Portfolio answer")
        groq_client_factory.assert_called_once_with(
            api_key="test-key",
            base_url=GROQ_API_BASE_URL,
            timeout=25,
            max_retries=1,
        )
        request = client.chat.completions.create.await_args.kwargs
        self.assertEqual(request["model"], "openai/gpt-oss-120b")
        self.assertEqual(request["max_completion_tokens"], 500)
        client.close.assert_awaited_once()

    def test_formats_provider_error_details_without_logging_credentials(self):
        test_credential = "gsk_" + ("x" * 32)
        body = {
            "error": {
                "type": "invalid_request_error",
                "code": "model_not_found",
                "message": f"Model error; token {test_credential}",
            }
        }

        details = _format_provider_error_body(body)

        self.assertIn("model_not_found", details)
        self.assertIn("[REDACTED]", details)
        self.assertNotIn(test_credential, details)


if __name__ == "__main__":
    unittest.main()
