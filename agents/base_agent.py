"""Shared base class for all Bedrock-backed agents."""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any

import boto3
from botocore.exceptions import ClientError
from rich.console import Console

from config import BEDROCK_REGION

console = Console()


class _StopAgent(Exception):
    """Raised by _dispatch_tool to signal the agent loop should terminate early."""


class BaseAgent(ABC):
    """Drives an AWS Bedrock model through an agentic tool-use loop via the Converse API."""

    def __init__(self, model: str, system_prompt: str, tools: list[dict],
                 max_tokens: int = 4096) -> None:
        self.client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Core agentic loop
    # ------------------------------------------------------------------

    def run(self, user_message: str, **kwargs: Any) -> Any:
        """Run the agent to completion and return the final parsed result."""
        messages: list[dict] = [
            {"role": "user", "content": [{"text": user_message}]}
        ]
        tool_config = (
            {"tools": [self._convert_tool(t) for t in self.tools]}
            if self.tools else None
        )

        while True:
            response = self._create_with_retry(messages, tool_config)
            stop_reason = response["stopReason"]
            output_content = response["output"]["message"]["content"]

            messages.append({"role": "assistant", "content": output_content})

            if stop_reason == "end_turn":
                for block in output_content:
                    if "text" in block:
                        return self._parse_result(block["text"])
                return None

            if stop_reason == "tool_use":
                tool_results: list[dict] = []
                early_stop = False

                for block in output_content:
                    if "toolUse" not in block:
                        continue
                    tu = block["toolUse"]
                    console.log(f"[dim][{self.__class__.__name__}] tool → {tu['name']}[/dim]")
                    try:
                        result = self._dispatch_tool(tu["name"], tu["input"])
                    except _StopAgent:
                        early_stop = True
                        result = {"status": "stopped"}

                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tu["toolUseId"],
                            "content": [{"text": json.dumps(result, ensure_ascii=False)}],
                        }
                    })

                if early_stop:
                    return self._parse_result("")

                messages.append({"role": "user", "content": tool_results})

    # ------------------------------------------------------------------
    # Throttle retry wrapper
    # ------------------------------------------------------------------

    def _create_with_retry(self, messages: list[dict], tool_config, max_retries: int = 4) -> Any:
        delay = 60
        kwargs: dict = dict(
            modelId=self.model,
            system=[{"text": self.system_prompt}],
            messages=messages,
            inferenceConfig={"maxTokens": self.max_tokens},
        )
        if tool_config:
            kwargs["toolConfig"] = tool_config

        for attempt in range(max_retries):
            try:
                return self.client.converse(**kwargs)
            except ClientError as exc:
                code = exc.response["Error"]["Code"]
                if code in ("ThrottlingException", "ServiceUnavailableException"):
                    if attempt == max_retries - 1:
                        raise
                    console.log(
                        f"[yellow][{self.__class__.__name__}] throttled — "
                        f"waiting {delay}s (attempt {attempt+1}/{max_retries})[/yellow]"
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 300)
                else:
                    raise
        raise RuntimeError("Unreachable")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _convert_tool(self, tool: dict) -> dict:
        """Convert from Anthropic tool format to Bedrock Converse toolSpec format."""
        return {
            "toolSpec": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "inputSchema": {
                    "json": tool.get("input_schema", {"type": "object", "properties": {}})
                },
            }
        }

    @abstractmethod
    def _dispatch_tool(self, name: str, inputs: dict) -> Any:
        """Route a tool-use call to the appropriate implementation."""

    def _parse_result(self, text: str) -> Any:
        t = (text or "").strip()
        if t.startswith("```"):
            t = t.split("\n", 1)[-1]
            t = t.rsplit("```", 1)[0].strip()
        try:
            return json.loads(t)
        except (json.JSONDecodeError, TypeError):
            return text
