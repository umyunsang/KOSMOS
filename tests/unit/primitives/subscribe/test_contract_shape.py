# SPDX-License-Identifier: Apache-2.0
"""T044 [P] — Contract shape test for subscribe input/output JSON schemas.

Loads specs/031-five-primitive-harness/contracts/subscribe.input.schema.json
and subscribe.output.schema.json; validates the 4-variant event union
and required fields against the schemas.
"""

from __future__ import annotations

import json
import pathlib

import pytest

# Path anchored to repo root via specs/ directory
# tests/unit/primitives/subscribe/test_contract_shape.py → parents[4] = repo root
_SPEC_CONTRACTS = (
    pathlib.Path(__file__).parents[4] / "specs" / "031-five-primitive-harness" / "contracts"
)
_INPUT_SCHEMA = _SPEC_CONTRACTS / "subscribe.input.schema.json"
_OUTPUT_SCHEMA = _SPEC_CONTRACTS / "subscribe.output.schema.json"


class TestSubscribeInputSchema:
    """T044 — SubscribeInput contract shape validation."""

    def test_schema_file_exists(self):
        assert _INPUT_SCHEMA.exists(), f"Missing contract: {_INPUT_SCHEMA}"

    def test_schema_loads_as_valid_json(self):
        schema = json.loads(_INPUT_SCHEMA.read_text())
        assert isinstance(schema, dict)

    def test_required_fields_present(self):
        schema = json.loads(_INPUT_SCHEMA.read_text())
        required = set(schema.get("required", []))
        assert "tool_id" in required
        assert "params" in required
        assert "lifetime_seconds" in required

    def test_tool_id_pattern(self):
        schema = json.loads(_INPUT_SCHEMA.read_text())
        tool_id = schema["properties"]["tool_id"]
        assert tool_id["minLength"] == 1
        assert tool_id["maxLength"] == 128
        assert "pattern" in tool_id

    def test_lifetime_seconds_bounds(self):
        schema = json.loads(_INPUT_SCHEMA.read_text())
        lifetime = schema["properties"]["lifetime_seconds"]
        assert lifetime["minimum"] == 1
        assert lifetime["maximum"] == 31536000  # 365 days ceiling (FR-011)

    def test_no_webhook_field(self):
        """FR-013 — no webhook/callback/receiver field anywhere in input schema."""
        schema = json.loads(_INPUT_SCHEMA.read_text())
        all_props = schema.get("properties", {})
        forbidden_names = {"webhook_url", "callback_url", "receiver_url", "inbound_url"}
        for name in forbidden_names:
            assert name not in all_props, f"Forbidden field {name!r} found in SubscribeInput"

    def test_additional_properties_false(self):
        schema = json.loads(_INPUT_SCHEMA.read_text())
        assert schema.get("additionalProperties") is False


class TestSubscribeOutputSchema:
    """T044 — SubscribeOutput contract shape validation (4-variant event union)."""

    def test_schema_file_exists(self):
        assert _OUTPUT_SCHEMA.exists(), f"Missing contract: {_OUTPUT_SCHEMA}"

    def test_schema_loads_as_valid_json(self):
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        assert isinstance(schema, dict)

    def test_required_fields_present(self):
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        required = set(schema.get("required", []))
        assert "handle" in required
        assert "events_schema" in required

    def test_subscription_handle_fields(self):
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        handle_def = schema["$defs"]["SubscriptionHandle"]
        handle_required = set(handle_def.get("required", []))
        assert "subscription_id" in handle_required
        assert "tool_id" in handle_required
        assert "opened_at" in handle_required
        assert "closes_at" in handle_required

    def test_four_event_variants_in_union(self):
        """Output schema must expose exactly 4 event variants (data-model.md §3)."""
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        events_schema = schema["properties"]["events_schema"]
        variants = events_schema.get("oneOf", [])
        variant_refs = {v["$ref"].split("/")[-1] for v in variants if "$ref" in v}
        expected = {
            "CbsBroadcastEvent",
            "RestPullTickEvent",
            "RssItemEvent",
            "SubscriptionBackpressureDrop",
        }
        assert variant_refs == expected, f"Expected {expected}, got {variant_refs}"

    def test_cbs_broadcast_event_shape(self):
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        cbs = schema["$defs"]["CbsBroadcastEvent"]
        required = set(cbs.get("required", []))
        assert {"kind", "cbs_message_id", "received_at", "payload_hash", "language", "body"} <= required
        assert cbs["properties"]["kind"]["const"] == "cbs_broadcast"
        # CBS message IDs must be the 3GPP range 4370–4385
        msg_ids = set(cbs["properties"]["cbs_message_id"]["enum"])
        assert msg_ids == set(range(4370, 4386))

    def test_rest_pull_tick_event_shape(self):
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        rpt = schema["$defs"]["RestPullTickEvent"]
        required = set(rpt.get("required", []))
        assert {"kind", "tool_id", "tick_at", "response_hash", "payload"} <= required
        assert rpt["properties"]["kind"]["const"] == "rest_pull_tick"

    def test_rss_item_event_shape(self):
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        rss = schema["$defs"]["RssItemEvent"]
        required = set(rss.get("required", []))
        assert {"kind", "feed_tool_id", "guid", "title"} <= required
        assert rss["properties"]["kind"]["const"] == "rss_item"

    def test_backpressure_drop_event_shape(self):
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        bp = schema["$defs"]["SubscriptionBackpressureDrop"]
        required = set(bp.get("required", []))
        assert {"kind", "subscription_id", "events_dropped", "message"} <= required
        assert bp["properties"]["kind"]["const"] == "subscription_backpressure_drop"
        assert bp["properties"]["events_dropped"]["minimum"] == 1

    def test_payload_hash_is_sha256_pattern(self):
        schema = json.loads(_OUTPUT_SCHEMA.read_text())
        cbs = schema["$defs"]["CbsBroadcastEvent"]
        pattern = cbs["properties"]["payload_hash"].get("pattern", "")
        assert "64" in pattern  # 64 hex chars for SHA-256
