"""
Unified OpenAI-compatible client for all three providers.
Returns (reply_text, usage_dict) or raises on error.
"""
import logging
from openai import OpenAI, OpenAIError
from config import PROVIDERS

logger = logging.getLogger(__name__)


def chat(
    provider_key: str,
    model_id: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict]:
    """
    Send chat request to the given provider.
    Returns (content, usage) where usage = {prompt_tokens, completion_tokens, total_tokens}.
    """
    provider = PROVIDERS[provider_key]
    client = OpenAI(api_key=provider["api_key"], base_url=provider["base_url"])

    logger.info("Request → provider=%s model=%s temp=%.2f max_tokens=%d msgs=%d",
                provider_key, model_id, temperature, max_tokens, len(messages))

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except OpenAIError as e:
        logger.error("OpenAI API error: %s", e)
        raise

    content = response.choices[0].message.content or ""
    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "finish_reason": response.choices[0].finish_reason,
        }

    logger.info("Response ← finish=%s tokens=%s", usage.get("finish_reason"), usage.get("total_tokens"))
    return content, usage
