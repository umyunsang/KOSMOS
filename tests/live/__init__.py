# SPDX-License-Identifier: Apache-2.0
"""Live API validation test package.

Tests in this package hit real external APIs (data.go.kr, KOROAD, FriendliAI)
and are gated behind the ``@pytest.mark.live`` marker.  They are skipped by
default and only execute when explicitly selected: ``pytest -m live``.
"""
