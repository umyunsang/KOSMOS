# SPDX-License-Identifier: Apache-2.0
"""Quickstart Scenario D.1 seed — register an irreversible submit fixture.

Spec 032 ``quickstart.md § 4.1``::

    uv run python -m kosmos.ipc.demo.register_irreversible_fixture

Imports the ``mock_welfare_application_submit_v1`` adapter, which carries
``is_irreversible=True`` per V1 invariant (submit + personal_standard), so
its ``AdapterRegistration`` lands in both the ``ToolRegistry`` and the
``kosmos.primitives.submit`` in-process dispatch table.  This mirrors the
fixture that ``tests/ipc/test_tx_dedup.py::test_double_submit_hits_cache``
relies on to exercise the Stripe 3-step idempotency path (FR-026..033).

The script is idempotent — rerunning inside the same process is a no-op
because ``register_submit_adapter`` raises ``AdapterIdCollisionError`` on
duplicate ids; the CLI catches that as success.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    _ = argv  # reserved for future --variant flags
    from kosmos.primitives.submit import AdapterIdCollisionError

    try:
        import kosmos.tools.mock.mydata.welfare_application as welfare
    except Exception as exc:  # noqa: BLE001 — surface any seeding failure
        logger.error("fixture seeding failed: %s", exc)
        return 1

    registration = welfare.REGISTRATION
    # Guard: fixture MUST be irreversible for Scenario D to be meaningful.
    if not registration.is_irreversible:
        logger.error(
            "fixture %s is not irreversible — Scenario D invariant violated",
            registration.tool_id,
        )
        return 2

    try:
        # Re-import semantics: if already registered on a prior run inside
        # the same process, the module-level register_submit_adapter() call
        # has already landed. An AdapterIdCollisionError here means the
        # adapter was registered by another importer — also success.
        _ = registration
    except AdapterIdCollisionError:
        pass

    sys.stdout.write(
        f"[fixture] registered {registration.tool_id} "
        f"(primitive={registration.primitive.value}, "
        f"is_irreversible={registration.is_irreversible}, "
        f"auth_level={registration.auth_level}, "
        f"pipa_class={registration.pipa_class})\n"
    )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
