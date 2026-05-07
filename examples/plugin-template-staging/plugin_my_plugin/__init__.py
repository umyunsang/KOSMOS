# SPDX-License-Identifier: Apache-2.0
"""UMMAYA plugin package: my_plugin.

NOTE: ``TOOL`` is intentionally NOT re-exported here. It is built
lazily at access time (PEP 562) by ``adapter.py`` so the scaffold's
tests can run without ``ummaya`` installed. Consumers that need the
GovAPITool entry should ``from .adapter import TOOL`` directly — the
UMMAYA host follows that convention.
"""

from .adapter import adapter
from .schema import LookupInput, LookupOutput

__all__ = ["adapter", "LookupInput", "LookupOutput"]
