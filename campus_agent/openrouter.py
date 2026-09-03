import json
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .network import prefer_ipv4



class ExtractionError(RuntimeError):
    pass


PROMPT = """Extract at most one campus-relevant event from this Ed Discussion thread. Return JSON only with: importance (low|medium|high), event_type, due_at (ISO-8601 or null), action_required (string or null), summary. If it has no concrete actionable or schedule/deadline/exam information, set importance to low and say that in summary. Do not invent dates.\n\nTHREAD:\n"""

DIGEST_PROMPT = """You are preparing a concise daily academic digest in Simplified Chinese.
Today is {today} in America/Los_Angeles. Review the extracted Ed events below.

Rules:
- Include only urgent or still-upcoming items. Exclude clearly past events.
- Merge duplicates about the same assignment, deadline, or signup; keep the most specific details.
- Treat extracted timezones cautiously: prefer the event wording, and do not invent missing dates.
- Use headings: `## 今天`, `## 接下来 7 天`, and, only if needed, `## 以后`.
- Under each heading, write short bullets beginning with the course code. Include required action and deadline/time when known.
- If there are no qualifying items for a heading, omit it. Do not mention filtering or the underlying system.

EVENTS:\n"""


def extract(thread: dict[str, Any], api_key: str, model: str) -> dict[str, Any]:
    if not api_key:
        raise ExtractionError("OPENROUTER_API_KEY is missing. Threads were stored locally; add the key and run sync again.")
    body = {"model": model, "messages": [{"role": "user", "content": PROMPT + json.dumps(thread, ensure_ascii=False)}], "response_format": {"type": "json_object"}}
    try:
        request = Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        with prefer_ipv4():
            with urlopen(request, timeout=60) as response:
                content = json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"]
        result = json.loads(content)
    except HTTPError as exc:
        if exc.code == 402:
            raise ExtractionError(
                "OpenRouter returned HTTP 402 (Payment Required). Add API credits or use a key with billing enabled; pending Ed threads remain stored locally."
            ) from exc
        raise ExtractionError(f"OpenRouter extraction failed: HTTP {exc.code}") from exc
    except (URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"OpenRouter extraction failed: {exc}") from exc
    if result.get("importance") not in {"low", "medium", "high"} or not result.get("summary"):
        raise ExtractionError("OpenRouter returned JSON that does not match the expected event shape.")
    return result


def create_digest(events: list[dict[str, Any]], api_key: str, model: str, today: date) -> str:
    if not api_key:
        raise ExtractionError("OPENROUTER_API_KEY is missing.")
    prompt = DIGEST_PROMPT.format(today=today.isoformat()) + json.dumps(events, ensure_ascii=False)
    body = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    try:
        request = Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
        with prefer_ipv4():
            with urlopen(request, timeout=60) as response:
                content = json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
    except HTTPError as exc:
        if exc.code == 402:
            raise ExtractionError("OpenRouter returned HTTP 402 (Payment Required).") from exc
        raise ExtractionError(f"OpenRouter digest failed: HTTP {exc.code}") from exc
    except (URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"OpenRouter digest failed: {exc}") from exc
    if not content:
        raise ExtractionError("OpenRouter returned an empty digest.")
    return content
