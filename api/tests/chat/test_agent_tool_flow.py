"""Verify the streaming loop produces the right events when the model calls the tool."""

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessageChunk

from macrohero.chat.agent import stream_chat


class _FakeStream:
    """Async iterator that emits a scripted sequence of LangChain chunks."""

    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        async def gen():
            for c in self._chunks:
                yield c

        return gen()


def _text_chunk(text: str) -> AIMessageChunk:
    return AIMessageChunk(content=text)


def _tool_call_chunk(tool_call_id: str, name: str, args: dict) -> AIMessageChunk:
    return AIMessageChunk(
        content="",
        tool_call_chunks=[
            {"id": tool_call_id, "name": name, "args": json.dumps(args), "index": 0}
        ],
    )


@pytest.mark.asyncio
async def test_stream_chat_emits_scenario_projection_part_when_tool_called(
    monkeypatch,
) -> None:
    pre_text = _text_chunk("I'll model Brent crude down 8%.")
    tool_call = _tool_call_chunk(
        "call_1",
        "run_factor_projection",
        {
            "pair": "USD/JPY",
            "horizon_days": 14,
            "factors": [{"name": "Brent crude", "expected_change": -8.0}],
        },
    )
    post_text = _text_chunk("Projection: -1.8% over 14 days.")

    pre_stream = _FakeStream([pre_text, tool_call])
    post_stream = _FakeStream([post_text])

    fake_llm = AsyncMock()
    fake_llm.astream = AsyncMock(side_effect=[pre_stream, post_stream])

    fake_result = {
        "pair": "USD/JPY",
        "horizon_days": 14,
        "regression_window_days": 252,
        "r_squared": 0.5,
        "intercept": 0.0,
        "factors": [],
        "projection": {
            "point_pct": -1.8,
            "band_95_low_pct": -4.0,
            "band_95_high_pct": 0.4,
            "spot_at_t0": 156.0,
            "projected_spot": 153.2,
            "spot_band_low": 150.0,
            "spot_band_high": 157.0,
        },
        "diagnostics": {"n_observations": 240, "warnings": [], "error": None},
    }

    with (
        patch("macrohero.chat.agent._make_llm", return_value=fake_llm),
        patch(
            "macrohero.chat.agent.run_factor_projection_impl",
            AsyncMock(return_value=fake_result),
        ),
    ):
        events: list[dict[str, Any]] = []
        async for evt in stream_chat(
            user_id="u1", db=None, messages=[{"role": "user", "content": "Hormuz war ends"}]
        ):
            events.append(evt)

    event_types = [e["type"] for e in events]
    assert "tool-input-available" in event_types
    assert "data-scenario_projection" in event_types
    final = next(e for e in events if e["type"] == "_final")
    part_kinds = [p["kind"] for p in final["parts"]]
    assert "scenario_projection" in part_kinds

    # Verify event order: pre-text comes before tool, tool input before data, data before narration
    assert event_types.index("tool-input-available") < event_types.index(
        "data-scenario_projection"
    )
    text_delta_indices = [i for i, t in enumerate(event_types) if t == "text-delta"]
    tool_idx = event_types.index("tool-input-available")
    data_idx = event_types.index("data-scenario_projection")
    pre_text_indices = [i for i in text_delta_indices if i < tool_idx]
    post_text_indices = [i for i in text_delta_indices if i > data_idx]
    assert pre_text_indices, "expected at least one text-delta before tool-input-available"
    assert post_text_indices, "expected at least one text-delta after data-scenario_projection"
