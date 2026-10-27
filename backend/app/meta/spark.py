"""Muse Spark structured-output calls with usage, cost and reasoning summaries (shown in the agent timeline)."""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from openai import AsyncOpenAI

from app.config import PRICES, SPARK_MODEL


def image_part(path: Path) -> dict:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "input_image", "image_url": f"data:image/jpeg;base64,{data}"}


def spark_cost(model: str, usage: dict) -> float:
    price = PRICES.get(model, PRICES["muse-spark-1.3"])
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0) or 0
    return ((usage.get("input_tokens", 0) - cached) * price["input"] + cached * price["cached"]
            + usage.get("output_tokens", 0) * price["output"])


async def spark_json(api: AsyncOpenAI, content: list[dict], schema: dict, name: str, *,
                     instructions: str, effort: str = "medium", max_tokens: int = 8000) -> tuple[dict, dict]:
    """One strict structured-output Responses call. Returns (parsed JSON, meta with usage/cost/summary)."""
    started = time.perf_counter()
    response = await api.responses.create(
        model=SPARK_MODEL,
        instructions=instructions,
        reasoning={"effort": effort, "summary": "auto"},
        max_output_tokens=max_tokens,
        input=[{"role": "user", "content": content}],
        text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}},
    )
    usage = response.usage.model_dump() if response.usage else {}
    summary = [part.text for item in response.output if item.type == "reasoning"
               for part in (getattr(item, "summary", None) or []) if getattr(part, "text", None)]
    meta = {"model": SPARK_MODEL, "seconds": round(time.perf_counter() - started, 1), "usage": usage,
            "cost_usd": spark_cost(SPARK_MODEL, usage), "reasoning_summary": summary}
    return json.loads(response.output_text), meta


async def spark_agent(api: AsyncOpenAI, content: list[dict], schema: dict, name: str, *, instructions: str,
                      tools: list[dict], handlers: dict, effort: str = "medium", max_tokens: int = 8000,
                      max_rounds: int = 4) -> tuple[dict, dict]:
    """Tool-calling loop that ends in a strict structured answer. `handlers[name](**args)` returns a JSON-able result.
    Arguments are validated by the handlers (tool `strict` only checks the schema). Rounds are capped."""
    started = time.perf_counter()
    usage_total: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
    cost, summary, calls = 0.0, [], []
    kwargs = dict(model=SPARK_MODEL, instructions=instructions, tools=tools, max_output_tokens=max_tokens,
                  reasoning={"effort": effort, "summary": "auto"},
                  text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}})
    response = await api.responses.create(input=[{"role": "user", "content": content}], **kwargs)
    for round_ in range(max_rounds + 1):
        usage = response.usage.model_dump() if response.usage else {}
        cost += spark_cost(SPARK_MODEL, usage)
        for key in usage_total:
            usage_total[key] += usage.get(key, 0) or 0
        summary += [p.text for item in response.output if item.type == "reasoning"
                    for p in (getattr(item, "summary", None) or []) if getattr(p, "text", None)]
        pending = [item for item in response.output if item.type == "function_call"]
        if not pending:
            break
        if round_ == max_rounds:
            raise RuntimeError(f"{name}: still calling tools after {max_rounds} rounds")
        outputs = []
        for call in pending:
            try:
                result = handlers[call.name](**json.loads(call.arguments or "{}"))
            except Exception as exc:  # bad tool name/arguments: tell the model instead of crashing the scan
                result = {"error": str(exc)[:300]}
            calls.append({"tool": call.name, "arguments": call.arguments})
            outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)})
        response = await api.responses.create(previous_response_id=response.id, input=outputs, **kwargs)
    meta = {"model": SPARK_MODEL, "seconds": round(time.perf_counter() - started, 1), "usage": usage_total,
            "cost_usd": cost, "reasoning_summary": summary, "tool_calls": calls}
    return json.loads(response.output_text), meta
