# SPDX-License-Identifier: Apache-2.0
"""KOSMOS plugin package: my_plugin."""

from .adapter import TOOL, adapter
from .schema import LookupInput, LookupOutput

__all__ = ["TOOL", "adapter", "LookupInput", "LookupOutput"]
