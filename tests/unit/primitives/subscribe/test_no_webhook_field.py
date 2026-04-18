# SPDX-License-Identifier: Apache-2.0
"""T045 [P] — FR-013: SubscribeInput must NOT contain any inbound-receiver URL field.

Recursively walks all fields of SubscribeInput and asserts that no field
accepts a URL that could act as an inbound receiver (webhook_url, callback_url,
receiver_url, etc.).

Allowed URL fields are those explicitly tagged as outbound-only by their field
name or description (e.g., ``rss_feed_url``, ``rest_pull_url``).
"""

from __future__ import annotations

import re

from kosmos.primitives.subscribe import SubscribeInput

# Pattern matching names that suggest inbound receiver / webhook semantics
_INBOUND_PATTERN = re.compile(
    r"(?i)(webhook|callback|receiver|inbound|notify|notification_url|push_url)"
)

# Patterns that are explicitly outbound-only (allowed even if they carry URL type)
_OUTBOUND_PATTERN = re.compile(r"(?i)(rss_feed_url|rest_pull_url|feed_url|polling_url|source_url)")


def _collect_url_fields(model_cls, visited=None):
    """Recursively collect all fields in a Pydantic model that could be URLs.

    Returns a list of (field_name, field_info) tuples for fields whose
    annotation includes any URL type (HttpUrl, AnyUrl, str with 'url' in name).
    """
    if visited is None:
        visited = set()
    if model_cls in visited:
        return []
    visited.add(model_cls)

    url_fields = []
    for name, field_info in model_cls.model_fields.items():
        annotation_str = str(field_info.annotation)
        # Collect if field name suggests URL or annotation includes URL type
        is_url_type = (
            "HttpUrl" in annotation_str or "AnyUrl" in annotation_str or "url" in name.lower()
        )
        if is_url_type:
            url_fields.append((name, field_info))

        # Recurse into nested Pydantic models if possible
        ann = field_info.annotation
        if ann is not None and hasattr(ann, "model_fields"):
            url_fields.extend(_collect_url_fields(ann, visited))

    return url_fields


class TestNoWebhookField:
    """T045 — FR-013 structural assertion."""

    def test_subscribe_input_importable(self):
        """SubscribeInput must be importable from kosmos.primitives.subscribe."""
        assert SubscribeInput is not None

    def test_no_inbound_receiver_field_by_name(self):
        """No field name in SubscribeInput may suggest inbound-webhook semantics."""
        for field_name in SubscribeInput.model_fields:
            assert not _INBOUND_PATTERN.search(field_name), (
                f"Field {field_name!r} in SubscribeInput looks like an inbound "
                "receiver URL (FR-013 violation). "
                "KOSMOS is a client-side harness — no webhook server."
            )

    def test_url_typed_fields_are_outbound_only(self):
        """Any URL-typed field must be explicitly outbound-only by name."""
        url_fields = _collect_url_fields(SubscribeInput)
        for field_name, field_info in url_fields:
            # If it's a URL field and doesn't match outbound pattern → fail
            if not _OUTBOUND_PATTERN.search(field_name):
                # Check description for explicit outbound-only annotation
                description = field_info.description or ""
                assert "outbound" in description.lower() or _OUTBOUND_PATTERN.search(field_name), (
                    f"URL field {field_name!r} in SubscribeInput is not tagged as "
                    "outbound-only. Add 'outbound' to description or rename to "
                    "e.g. 'rss_feed_url' / 'rest_pull_url'. (FR-013)"
                )

    def test_model_forbids_extra_fields(self):
        """extra='forbid' prevents runtime injection of webhook fields."""
        config = SubscribeInput.model_config
        assert config.get("extra") == "forbid", (
            "SubscribeInput must set extra='forbid' to prevent runtime "
            "injection of webhook fields (FR-013 defense-in-depth)."
        )

    def test_webhook_url_field_absent(self):
        """Explicit check: 'webhook_url' must not exist as a field."""
        assert "webhook_url" not in SubscribeInput.model_fields

    def test_callback_url_field_absent(self):
        assert "callback_url" not in SubscribeInput.model_fields

    def test_receiver_url_field_absent(self):
        assert "receiver_url" not in SubscribeInput.model_fields
