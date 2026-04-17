# SPDX-License-Identifier: Apache-2.0
"""T012 — RED test for `kosmos.prompt.hash` OTEL span attribute (FR-C07, SC-007).

Strategy
--------
Drive a minimal Context Assembly → LLMClient call through an httpx.MockTransport
(intercepts all outbound HTTP, no live network) and an in-memory OTEL span
exporter (monkeypatches the module-level _tracer in kosmos.llm.client following
the proven pattern from test_llm_chat_span.py).

Two test cases:

T012-A  test_prompt_hash_attribute_emitted_on_llm_call
        Assert that at least one finished span carries the attribute
        ``kosmos.prompt.hash``.  This test FAILS RED now because T032 has not
        yet wired the attribute emission.

T012-B  test_prompt_hash_equals_sha256_of_sent_bytes
        Capture the raw JSON body intercepted by MockTransport, extract
        ``messages[0].content`` (the system prompt string), encode as UTF-8,
        compute SHA-256 hex digest, and assert it equals the span's
        ``kosmos.prompt.hash`` attribute value.  Also FAILs RED now.

Expected failure modes (RED phase)
-----------------------------------
* ``PromptLoader`` import fails (T025 not yet implemented) — test collection
  error surfaces as ImportError in the ``from kosmos.context.prompt_loader …``
  import inside the test body.
* Alternatively if import is skipped, the span attribute is simply absent →
  ``AssertionError: kosmos.prompt.hash not found in span attributes``.

Both are intentional.  T032 is the implementation task that makes this green.

Architecture
------------
``SystemPromptAssembler.assemble()`` (src/kosmos/context/system_prompt.py)
    produces the system prompt string.
``PromptLoader`` (src/kosmos/context/prompt_loader.py — T025, not yet present)
    will expose ``.get_hash(prompt_id) -> str`` and ``.all_hashes()``.
``LLMClient.complete()`` (src/kosmos/llm/client.py)
    sends the OpenAI-compatible JSON body; the ``stream()`` path creates the
    ``chat`` span; ``complete()`` does NOT create its own span (no _tracer call
    in the non-streaming path — see client.py).  The test therefore uses
    ``stream()`` for span coverage, which mirrors the production call path.
The span emitting ``kosmos.prompt.hash`` is expected on the ``chat`` span
created inside ``LLMClient.stream()``.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from kosmos.context.models import SystemPromptConfig
from kosmos.context.system_prompt import SystemPromptAssembler
from kosmos.llm.models import ChatMessage, StreamEvent

# ---------------------------------------------------------------------------
# Attempt to import PromptLoader — this import will FAIL RED until T025 lands.
# The ImportError is the primary expected failure mode during Phase 3.2.
# ---------------------------------------------------------------------------
try:
    from kosmos.context.prompt_loader import PromptLoader  # type: ignore[import]

    _PROMPT_LOADER_AVAILABLE = True
except ImportError:
    _PROMPT_LOADER_AVAILABLE = False
    PromptLoader = None  # type: ignore[assignment,misc]

# OTEL attribute name defined in the KOSMOS extension namespace (FR-C07, Spec 021).
_KOSMOS_PROMPT_HASH_ATTR = "kosmos.prompt.hash"

# Minimal valid env so LLMClientConfig loads without touching the network.
_FAKE_ENV = {"KOSMOS_FRIENDLI_TOKEN": "test-token-for-t012"}

# Fixed streaming SSE response that MockTransport returns for every POST.
_SSE_LINES = [
    b'data: {"id":"cmpl-t012","object":"chat.completion.chunk","model":"LGAI-EXAONE/K-EXAONE-236B-A23B","choices":[{"index":0,"delta":{"role":"assistant","content":"OK."},"finish_reason":null}]}\n\n',  # noqa: E501 — SSE wire fixture; breaking alters payload
    b'data: {"id":"cmpl-t012","object":"chat.completion.chunk","model":"LGAI-EXAONE/K-EXAONE-236B-A23B","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":3}}\n\n',  # noqa: E501 — SSE wire fixture; breaking alters payload
    b"data: [DONE]\n\n",
]


# ---------------------------------------------------------------------------
# Helpers: captured request body store
# ---------------------------------------------------------------------------


class _CapturingTransport(httpx.AsyncBaseTransport):
    """MockTransport that records the raw request body of every POST.

    Returns a minimal streaming SSE response so LLMClient.stream() can
    complete without errors.  No real network traffic is made.
    """

    def __init__(self) -> None:
        self.captured_bodies: list[bytes] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        body_bytes = await request.aread()
        self.captured_bodies.append(body_bytes)

        # Concatenate all SSE lines into a single bytes payload.
        payload = b"".join(_SSE_LINES)
        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/event-stream"},
            content=payload,
        )


# ---------------------------------------------------------------------------
# Fixture: per-test InMemorySpanExporter monkeypatching _tracer
# (pattern from test_llm_chat_span.py and test_tool_execute_span.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    """Patch _tracer in kosmos.llm.client with a dedicated test TracerProvider."""
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    import kosmos.llm.client as client_mod

    monkeypatch.setattr(client_mod, "_tracer", provider.get_tracer("kosmos.llm.client"))
    exporter.clear()
    return exporter


# ---------------------------------------------------------------------------
# Helper: build LLMClient with MockTransport injected
# ---------------------------------------------------------------------------


def _make_client_with_transport(
    transport: _CapturingTransport,
) -> Any:
    """Construct an LLMClient whose internal httpx.AsyncClient uses transport.

    LLMClient builds self._client internally, so we construct normally then
    replace the internal _client with a fresh AsyncClient backed by the
    test transport.  The base_url must match so relative /chat/completions
    resolves correctly.
    """
    from kosmos.llm.client import LLMClient
    from kosmos.llm.config import LLMClientConfig

    with patch.dict(os.environ, _FAKE_ENV):
        config = LLMClientConfig()

    client = LLMClient(config=config)
    # Replace the internal AsyncClient with one backed by our capturing transport.
    client._client = httpx.AsyncClient(  # type: ignore[attr-defined]
        base_url=str(config.base_url),
        transport=transport,
        timeout=httpx.Timeout(5.0),
    )
    return client


# ---------------------------------------------------------------------------
# Helper: assemble system prompt using the current SystemPromptAssembler
# (the path that T030 will refactor to use PromptLoader)
# ---------------------------------------------------------------------------


def _assemble_system_prompt() -> str:
    """Return the system prompt string exactly as Context Assembly produces it."""
    assembler = SystemPromptAssembler()
    config = SystemPromptConfig()
    return assembler.assemble(config)


# ---------------------------------------------------------------------------
# T012-A: kosmos.prompt.hash attribute is present on the chat span
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prompt_hash_attribute_emitted_on_llm_call(
    mem_exporter: InMemorySpanExporter,
) -> None:
    """Assert that a span from the Context Assembly layer carries kosmos.prompt.hash.

    EXPECTED FAILURE (RED): The attribute is not yet stamped — T032 wires it.
    Additionally, if PromptLoader is not yet importable (T025 not done), this
    test may surface as an ImportError at collection time, which is also an
    acceptable RED failure mode.
    """
    # The import of PromptLoader above is the first gate: if T025 is not done
    # the module-level import already failed and this test is skipped with the
    # ImportError surfacing at collection.  Assert here so the failure is
    # explicit even if collection somehow continued.
    assert _PROMPT_LOADER_AVAILABLE, (
        "PromptLoader not importable — kosmos.context.prompt_loader does not exist yet. "
        "T025 must be implemented before T032 can make this test green."
    )

    transport = _CapturingTransport()
    client = _make_client_with_transport(transport)

    system_prompt = _assemble_system_prompt()
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content="사고 정보 알려줘"),
    ]

    events: list[StreamEvent] = []
    async with client:
        async for event in client.stream(messages):
            events.append(event)

    # Retrieve all finished spans.
    spans = mem_exporter.get_finished_spans()
    assert spans, "No spans were exported — is the _tracer monkeypatch in effect?"

    # Find all spans from the Context Assembly layer (identified by kosmos.prompt.hash).
    # T032 will stamp this attribute on the 'chat' span produced by LLMClient.stream().
    hash_attrs = [
        dict(s.attributes or {}).get(_KOSMOS_PROMPT_HASH_ATTR)
        for s in spans
        if _KOSMOS_PROMPT_HASH_ATTR in (s.attributes or {})
    ]

    # PRIMARY ASSERTION — fails RED until T032 is implemented.
    assert hash_attrs, (
        f"{_KOSMOS_PROMPT_HASH_ATTR!r} not found in any span attribute. "
        f"Exported spans: {[(s.name, dict(s.attributes or {})) for s in spans]}. "
        "T032 must stamp this attribute on the 'chat' span before this test goes green."
    )


# ---------------------------------------------------------------------------
# T012-B: hash value equals SHA-256 of system prompt bytes sent in call body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prompt_hash_equals_sha256_of_sent_bytes(
    mem_exporter: InMemorySpanExporter,
) -> None:
    """Assert kosmos.prompt.hash == sha256(messages[0].content.encode('utf-8')).

    The spec says the hash covers the system prompt bytes ACTUALLY SENT — i.e.
    the UTF-8 encoding of the ``messages[0].content`` field in the OpenAI-
    compatible JSON body, NOT the whole body.

    EXPECTED FAILURE (RED): Attribute not yet stamped (T032) and PromptLoader
    not yet importable (T025).
    """
    assert _PROMPT_LOADER_AVAILABLE, "PromptLoader not importable — T025 must be implemented first."

    transport = _CapturingTransport()
    client = _make_client_with_transport(transport)

    system_prompt = _assemble_system_prompt()
    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content="강남역 사고 알려줘"),
    ]

    events: list[StreamEvent] = []
    async with client:
        async for event in client.stream(messages):
            events.append(event)

    # --- Compute expected hash from the captured request body ---
    assert transport.captured_bodies, (
        "MockTransport captured no request bodies — LLMClient did not POST to the mock."
    )
    raw_body = transport.captured_bodies[0]
    body_json: dict[str, Any] = json.loads(raw_body)

    # Extract system prompt from messages[0].content as sent in the wire payload.
    sent_messages: list[dict[str, Any]] = body_json.get("messages", [])
    assert sent_messages, f"'messages' field missing or empty in captured body: {body_json}"

    system_msg = sent_messages[0]
    assert system_msg.get("role") == "system", (
        f"Expected messages[0].role == 'system', got {system_msg.get('role')!r}. "
        f"Full messages: {sent_messages}"
    )
    system_content: str = system_msg.get("content", "")
    assert system_content, "messages[0].content is empty — system prompt was not sent."

    expected_hash = hashlib.sha256(system_content.encode("utf-8")).hexdigest()

    # --- Find the kosmos.prompt.hash attribute on any exported span ---
    spans = mem_exporter.get_finished_spans()
    assert spans, "No spans were exported."

    actual_hash: str | None = None
    for span in spans:
        attrs = dict(span.attributes or {})
        if _KOSMOS_PROMPT_HASH_ATTR in attrs:
            actual_hash = str(attrs[_KOSMOS_PROMPT_HASH_ATTR])
            break

    # PRIMARY ASSERTION — fails RED until T032 is implemented.
    assert actual_hash is not None, (
        f"{_KOSMOS_PROMPT_HASH_ATTR!r} not found on any span. "
        f"Exported spans: {[(s.name, dict(s.attributes or {})) for s in spans]}. "
        "T032 must stamp this attribute on the 'chat' span."
    )

    # SECONDARY ASSERTION — hash value correctness.
    assert actual_hash == expected_hash, (
        f"Hash mismatch: span has {actual_hash!r} "
        f"but SHA-256 of sent system prompt bytes is {expected_hash!r}. "
        f"System prompt (first 120 chars): {system_content[:120]!r}"
    )
