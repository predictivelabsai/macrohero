"""Session title generation.

When a chat session receives its first user message we run a one-shot
completion against the flash deepseek model to produce a short, descriptive
title. The flash variant is used (not the pro one that drives the agent) so
the call is cheap and finishes in well under a second on typical input.

The function is intentionally tolerant: any error (missing key, HTTP failure,
timeout, schema mismatch) is logged and `None` is returned. Callers fall back
to whatever placeholder title they wrote before kicking off this task.
"""

import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from macrohero.config import get_settings

logger = logging.getLogger(__name__)

# DB column is String(200); we hard-cap output to fit even if the model ignores
# the prompt's length guidance.
_TITLE_HARD_CAP = 200
_TIMEOUT_SECONDS = 15.0

_SYSTEM_PROMPT = """You write short titles for chat sessions.

Given the user's first message, output a single descriptive title that names the topic. Rules:

- 4 to 12 words. Aim for under 80 characters; never exceed 180.
- Preserve specific entities the user mentioned (currencies, instruments, dates, events).
- Sentence case. No surrounding quotes, no trailing punctuation, no emoji.
- Output only the title text. No prefix, no explanation, no newline."""


def _clean(raw: str) -> str:
    text = raw.strip().strip('"\'').strip()
    text = text.splitlines()[0] if text else text
    text = text.rstrip(" .,:;…")
    if len(text) > _TITLE_HARD_CAP:
        text = text[:_TITLE_HARD_CAP].rstrip()
    return text


async def summarize_title(content: str) -> str | None:
    """Run the flash LLM to produce a session title. Returns ``None`` on any
    error so the caller can keep the placeholder title."""
    settings = get_settings()
    if not settings.deepseek_api_key:
        logger.warning("summarize_title skipped: DEEPSEEK_API_KEY not configured")
        return None

    cleaned_input = " ".join(content.split())
    if not cleaned_input:
        return None

    llm = ChatOpenAI(
        model=settings.deepseek_flash_model,
        api_key=SecretStr(settings.deepseek_api_key),
        base_url=settings.deepseek_base_url,
        temperature=0.1,
        max_completion_tokens=80,
        streaming=False,
    )

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=cleaned_input),
    ]

    try:
        response = await asyncio.wait_for(llm.ainvoke(messages), timeout=_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.warning("summarize_title timed out after %.0fs", _TIMEOUT_SECONDS)
        return None
    except Exception:
        logger.exception("summarize_title failed")
        return None

    raw = response.content if isinstance(response.content, str) else ""
    title = _clean(raw)
    if not title:
        logger.warning("summarize_title produced empty output for content=%r", cleaned_input[:80])
        return None
    return title
