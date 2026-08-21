from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from typing import Any

from agent.memory_provider import MemoryProvider, RecallStatus


class FastBrainProvider(MemoryProvider):
    def __init__(self) -> None:
        self.url = ""
        self.api_key = ""
        self.agent_id = "hermes"
        self.device_id = ""
        self.session_id = ""
        self._last_count = 0

    @property
    def name(self) -> str:
        return "fast-brain"

    def is_available(self) -> bool:
        return bool(os.environ.get("FAST_BRAIN_URL") and os.environ.get("FAST_BRAIN_API_KEY"))

    def unavailable_reason(self) -> str:
        return "Set FAST_BRAIN_URL and FAST_BRAIN_API_KEY in the Hermes profile .env"

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        self.url = os.environ["FAST_BRAIN_URL"].rstrip("/")
        self.api_key = os.environ["FAST_BRAIN_API_KEY"]
        self.agent_id = os.environ.get("FAST_BRAIN_AGENT_ID") or kwargs.get("agent_workspace") or "hermes"
        self.device_id = os.environ.get("FAST_BRAIN_DEVICE_ID") or kwargs.get("agent_identity") or "hermes"
        self.session_id = session_id

    def get_config_schema(self) -> list[dict[str, Any]]:
        return [
            {"key": "url", "description": "fast-brain API URL", "required": True, "env_var": "FAST_BRAIN_URL"},
            {
                "key": "api_key",
                "description": "fast-brain API key",
                "secret": True,
                "required": True,
                "env_var": "FAST_BRAIN_API_KEY",
            },
            {
                "key": "agent_id",
                "description": "Shared memory namespace, e.g. hermes or hermes-coder",
                "default": "hermes",
                "env_var": "FAST_BRAIN_AGENT_ID",
            },
            {
                "key": "device_id",
                "description": "This Hermes instance/device label",
                "default": "hermes",
                "env_var": "FAST_BRAIN_DEVICE_ID",
            },
        ]

    def save_config(self, values: dict[str, Any], hermes_home: str) -> None:
        return None

    def system_prompt_block(self) -> str:
        return (
            "fast-brain external semantic memory is active. Use fb_search_memory for explicit recall "
            "and fb_remember for durable facts worth keeping."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        results = self._request("POST", "/v1/search", {"query": query, "agent_id": self.agent_id, "limit": 5})
        self._last_count = len(results) if isinstance(results, list) else 0
        if not self._last_count:
            return ""
        lines = [f"- {item.get('content', '')}" for item in results if item.get("content")]
        return "Relevant fast-brain memories:\n" + "\n".join(lines)

    def recall_status(self) -> RecallStatus | None:
        if not self._last_count:
            return None
        return RecallStatus(provider_label="fast-brain", count=self._last_count)

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: list[dict[str, Any]] | None = None,
    ) -> None:
        sid = session_id or self.session_id

        def sync() -> None:
            self._request(
                "POST",
                "/v1/messages",
                {
                    "session_id": sid,
                    "role": "user",
                    "content": user_content,
                    "agent_id": self.agent_id,
                    "device_id": self.device_id,
                },
            )
            self._request(
                "POST",
                "/v1/messages",
                {
                    "session_id": sid,
                    "role": "assistant",
                    "content": assistant_content,
                    "agent_id": self.agent_id,
                    "device_id": self.device_id,
                },
            )

        threading.Thread(target=sync, daemon=True).start()

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "fb_search_memory",
                "description": "Search fast-brain semantic memory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "fb_remember",
                "description": "Store a durable memory in fast-brain.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "kind": {"type": "string", "default": "fact"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "fb_forget",
                "description": "Delete a fast-brain memory by id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                    },
                    "required": ["id"],
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs: Any) -> str:
        if tool_name == "fb_search_memory":
            result = self._request(
                "POST",
                "/v1/search",
                {"query": args["query"], "agent_id": self.agent_id, "limit": args.get("limit", 5)},
            )
            return json.dumps({"memories": result}, ensure_ascii=False)
        if tool_name == "fb_remember":
            result = self._request(
                "POST",
                "/v1/memories",
                {
                    "content": args["content"],
                    "agent_id": self.agent_id,
                    "session_id": kwargs.get("session_id") or self.session_id,
                    "kind": args.get("kind", "fact"),
                },
            )
            return json.dumps(result, ensure_ascii=False)
        if tool_name == "fb_forget":
            result = self._request("DELETE", f"/v1/memories/{args['id']}?agent_id={self.agent_id}", {})
            return json.dumps(result, ensure_ascii=False)
        raise NotImplementedError(tool_name)

    def _request(self, method: str, path: str, payload: dict[str, Any]) -> Any:
        data = None if method == "DELETE" else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{self.url}{path}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {"error": str(exc)}


def register(ctx: Any) -> None:
    ctx.register_memory_provider(FastBrainProvider())
