"""OpenAI Responses API adapter."""

from __future__ import annotations

import json
from typing import Any, cast

from openai import AsyncOpenAI

from opspilot.agent.models import ModelDecision, ToolCall


class ResponsesModel:
    """Minimal Responses API model adapter with normalized tool decisions."""

    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.previous_response_id: str | None = None

    async def next_async(
        self, input_items: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> tuple[ModelDecision, Any]:
        create = cast(Any, self.client.responses.create)
        response = await create(
            model=self.model,
            input=input_items,
            tools=tools,
            tool_choice="auto",
            previous_response_id=self.previous_response_id,
        )
        self.previous_response_id = response.id
        for item in response.output:
            if getattr(item, "type", None) == "function_call":
                return (
                    ModelDecision(
                        kind="tool_call",
                        tool_call=ToolCall(
                            name=item.name,
                            arguments=json.loads(item.arguments),
                            call_id=item.call_id,
                        ),
                    ),
                    response,
                )
        return ModelDecision(kind="final", text=response.output_text), response
