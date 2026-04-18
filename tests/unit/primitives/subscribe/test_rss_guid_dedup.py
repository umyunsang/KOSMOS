# SPDX-License-Identifier: Apache-2.0
"""T050 [P] — RSS guid de-duplication: duplicate guids suppressed; reset guid = new item.

Validates Edge Case from research.md §4:
  "System MUST treat reset guids as new items — delivery is the safer default."
"""

from __future__ import annotations

import asyncio

import pytest

from kosmos.primitives.subscribe import RssGuidTracker, RssItemEvent


class TestRssGuidDedup:
    """T050 — RSS guid de-duplication within a subscription handle."""

    def test_tracker_accepts_new_guid(self):
        """A guid not yet seen must be reported as new."""
        tracker = RssGuidTracker()
        assert tracker.is_new("guid-001") is True

    def test_tracker_suppresses_duplicate_guid(self):
        """A guid seen before must be suppressed."""
        tracker = RssGuidTracker()
        tracker.mark_seen("guid-001")
        assert tracker.is_new("guid-001") is False

    def test_tracker_accepts_different_guid(self):
        """Different guids are independent."""
        tracker = RssGuidTracker()
        tracker.mark_seen("guid-001")
        assert tracker.is_new("guid-002") is True

    def test_tracker_reset_guid_surfaces_as_new(self):
        """After reset(), a previously-seen guid must be treated as new (Edge Case).

        This covers the case where the publisher reuses a guid value for
        different content — KOSMOS delivers it again to avoid silent gap.
        """
        tracker = RssGuidTracker()
        tracker.mark_seen("guid-001")
        assert tracker.is_new("guid-001") is False
        tracker.reset()
        # After reset, the same guid is "new" again
        assert tracker.is_new("guid-001") is True

    def test_tracker_reset_clears_all_seen(self):
        """reset() clears all tracked guids, not just the last one."""
        tracker = RssGuidTracker()
        for i in range(10):
            tracker.mark_seen(f"guid-{i:03d}")
        tracker.reset()
        for i in range(10):
            assert tracker.is_new(f"guid-{i:03d}") is True

    def test_tracker_is_per_subscription_state(self):
        """Two RssGuidTracker instances are independent."""
        t1 = RssGuidTracker()
        t2 = RssGuidTracker()
        t1.mark_seen("guid-shared")
        assert t2.is_new("guid-shared") is True, "Trackers must not share state"

    def test_tracker_marks_seen_on_is_new(self):
        """is_new() must auto-mark the guid as seen in one call."""
        tracker = RssGuidTracker()
        # First call: is_new=True and marks seen
        assert tracker.is_new("guid-auto") is True
        # Second call: same guid, now suppressed
        assert tracker.is_new("guid-auto") is False

    def test_multiple_items_deduplicated_correctly(self):
        """Simulate a batch with duplicates: only novel guids pass."""
        tracker = RssGuidTracker()
        guids_in = ["a", "b", "a", "c", "b", "d", "a"]
        guids_out = [g for g in guids_in if tracker.is_new(g)]
        assert guids_out == ["a", "b", "c", "d"]
