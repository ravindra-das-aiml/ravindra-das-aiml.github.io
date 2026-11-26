import json
import logging
import re

from groq import APIConnectionError, APITimeoutError, AsyncGroq, RateLimitError
from groq import APIStatusError

from app.core.config import get_settings
from app.schemas.chat import ChatMessage
from app.services.portfolio_context import build_system_prompt


logger = logging.getLogger(__name__)
GROQ_API_BASE_URL = "https://api.groq.com"


def _format_provider_error_body(body: object) -> str:
    if not isinstance(body, dict):
        return "No structured error details were returned."

    details = body.get("error")
    if not isinstance(details, dict):
        return "No structured error details were returned."

    safe_details = {
        field: details[field]
        for field in ("type", "code", "message")
        if isinstance(details.get(field), (str, int, float))
    }
    if not safe_details:
        return "No structured error details were returned."

    formatted = json.dumps(safe_details, ensure_ascii=False, sort_keys=True)
    return re.sub(
        r"(?i)(gsk_[A-Za-z0-9_-]+|Bearer\s+\S+)",
        "[REDACTED]",
        formatted,
    )[:1000]


class GroqServiceError(Exception):
    def __init__(self, status_code: int, public_message: str):
        super().__init__(public_message)
        self.status_code = status_code
        self.public_message = public_message


async def generate_reply(messages: list[ChatMessage]) -> str:
    settings = get_settings()
    client = AsyncGroq(
        api_key=settings.groq_api_key.get_secret_value(),
        base_url=GROQ_API_BASE_URL,
        timeout=settings.groq_timeout_seconds,
        max_retries=1,
    )

    try:
        completion = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": build_system_prompt()},
                *[
                    {"role": message.role, "content": message.content}
                    for message in messages
                ],
            ],
            temperature=0.2,
            max_completion_tokens=500,
        )
    except APITimeoutError as error:
        raise GroqServiceError(
            504, "The assistant timed out. Please try again."
        ) from error
    except RateLimitError as error:
        logger.warning("Groq rate limit reached.")
        raise GroqServiceError(
            503, "The assistant is temporarily busy. Please try again shortly."
        ) from error
    except APIStatusError as error:
        logger.warning(
            "Groq API error (status %s): %s",
            error.status_code,
            _format_provider_error_body(error.body),
        )
        if error.status_code == 404:
            raise GroqServiceError(
                502,
                "The configured Groq model or API endpoint is unavailable. "
                "Check the backend Groq configuration.",
            ) from error
        raise GroqServiceError(
            502, "The assistant is temporarily unavailable."
        ) from error
    except APIConnectionError as error:
        logger.warning("Could not connect to Groq.")
        raise GroqServiceError(
            502, "The assistant is temporarily unavailable."
        ) from error
    finally:
        await client.close()

    reply = completion.choices[0].message.content
    if not reply or not reply.strip():
        raise GroqServiceError(502, "The assistant returned an empty response.")
    return reply.strip()
