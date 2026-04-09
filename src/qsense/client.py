"""OpenAI-compatible API client for multimodal chat completions."""

from __future__ import annotations

import re
import sys

from openai import APIError, OpenAI, Stream

from .config import Config
from .models import get_model


def _collect_stream(stream: Stream) -> str:
    """Consume a streaming response and return the full text."""
    parts: list[str] = []
    for chunk in stream:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                parts.append(delta.content)
    return "".join(parts)


def _strip_thinking(text: str) -> str:
    """Remove leading <think>...</think> blocks from reasoning models."""
    return re.sub(r"^\s*(<think>[\s\S]*?</think>\s*)+", "", text).strip()


def _format_api_error(exc: Exception) -> str:
    """Format an API error for display without leaking sensitive details."""
    if isinstance(exc, APIError):
        msg = getattr(exc, "message", None) or str(exc.body) if exc.body else ""
        return f"HTTP {exc.status_code}: {msg}" if exc.status_code else str(msg)
    return str(exc)


def chat(
    config: Config,
    prompt: str,
    images: list[dict] | None = None,
    audios: list[dict] | None = None,
    extras: list[dict] | None = None,
) -> str:
    """Send a multimodal request and return the assistant's text reply."""
    client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    message_content: list[dict] = [{"type": "text", "text": prompt}]
    if images:
        message_content.extend(images)
    if audios:
        message_content.extend(audios)
    if extras:
        message_content.extend(extras)

    kwargs = dict(
        model=config.model,
        messages=[{"role": "user", "content": message_content}],
        timeout=config.timeout,
    )

    model_info = get_model(config.model)
    use_stream = model_info.stream_only if model_info else False

    try:
        if use_stream:
            response = client.chat.completions.create(**kwargs, stream=True)
        else:
            response = client.chat.completions.create(**kwargs, stream=False)
    except Exception as exc:
        if not use_stream and "stream" in str(exc).lower():
            try:
                response = client.chat.completions.create(**kwargs, stream=True)
            except Exception as exc2:
                print(f"[qsense] {_format_api_error(exc2)}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"[qsense] {_format_api_error(exc)}", file=sys.stderr)
            sys.exit(1)

    if isinstance(response, Stream):
        text = _collect_stream(response)
    elif isinstance(response, str):
        text = response
    else:
        text = response.choices[0].message.content if response.choices else None

    if not text:
        print("[qsense] No assistant text found in response.", file=sys.stderr)
        sys.exit(1)

    return _strip_thinking(text)
