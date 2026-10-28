"""Mistral client that stays under the API rate limit."""

import os
import time

import httpx
from langchain_mistralai import ChatMistralAI

# Experiment-tier keys are often limited to about one request per second.
_MIN_GAP_SECONDS = 1.5
_last_call = 0.0


def _pace() -> None:
    global _last_call
    wait = _MIN_GAP_SECONDS - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def _retry_after_seconds(exc: httpx.HTTPStatusError, fallback: float) -> float:
    header = exc.response.headers.get("retry-after")
    if header:
        try:
            return max(float(header), 1.0)
        except ValueError:
            pass
    return fallback


class RateLimitedChatMistralAI(ChatMistralAI):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        delay = 5.0
        for attempt in range(6):
            _pace()
            try:
                return super()._generate(
                    messages, stop=stop, run_manager=run_manager, **kwargs
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429 or attempt == 5:
                    raise
                time.sleep(_retry_after_seconds(exc, delay))
                delay = min(delay * 2, 60.0)


def get_llm(temperature: float = 0.3) -> RateLimitedChatMistralAI:
    return RateLimitedChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=temperature,
    )
