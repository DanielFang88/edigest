"""Read-only adapter around the third-party ``edapi`` package.

The adapter deliberately exposes only the three GET-style operations needed by
the campus agent. It never calls edapi's create, edit, upload, lock, or unlock
methods.
"""
from typing import Any

import requests
from edapi import EdAPI
from edapi.types import EdAuthError, EdError

from .network import prefer_ipv4


class EdAPIError(RuntimeError):
    pass


class EdClient:
    def __init__(self, token: str):
        if not token:
            raise EdAPIError("ED_API_TOKEN is missing. Add it to .env locally.")
        # Passing the token directly means edapi does not search other .env
        # files. interactive=False guarantees a scheduled run never prompts.
        self.client = EdAPI(api_token=token, interactive=False)
        # edapi 0.1.0 only installs this header when it loads a token from its
        # own .env file, not when a caller passes ``api_token`` directly.
        # Add the ordinary documented Bearer header once for this session.
        self.client.session.headers.update({"Authorization": f"Bearer {token}"})

    def _call(self, method, *args, **kwargs):
        try:
            # Ed's library does not expose a network-family option. Prefer
            # IPv4 on this laptop because its IPv6 route has been verified to
            # time out while the same Ed host responds over IPv4.
            with prefer_ipv4():
                return method(*args, **kwargs)
        except EdAuthError as exc:
            raise EdAPIError("Ed rejected the API token. Generate a fresh token in Ed Settings and try once.") from exc
        except EdError as exc:
            response = getattr(exc, "args", [{}])[0]
            message = response.get("message", "Ed API request failed.") if isinstance(response, dict) else "Ed API request failed."
            if isinstance(response, dict) and response.get("response", {}).get("error_name") == "browser_signature_banned":
                message = "Ed/Cloudflare blocked this automated client (Error 1010). Stop retrying and contact Ed support."
            raise EdAPIError(message) from exc
        except requests.RequestException as exc:
            raise EdAPIError(f"Could not reach Ed API: {exc}") from exc

    def courses(self) -> list[dict[str, Any]]:
        payload = self._call(self.client.get_user_info)
        result = []
        for enrollment in payload.get("courses", []):
            course = dict(enrollment.get("course") or {})
            if course:
                course["enrollment_role"] = (enrollment.get("role") or {}).get("role", "")
                result.append(course)
        return result

    def threads(self, course_id: int, limit: int = 100) -> list[dict[str, Any]]:
        return list(self._call(self.client.list_threads, course_id, limit=min(limit, 100), sort="new"))

    def thread(self, thread_id: int) -> dict[str, Any]:
        payload = self._call(self.client.get_thread, thread_id)
        thread = dict(payload.get("thread", payload))
        thread["_users"] = payload.get("users", [])
        return thread
