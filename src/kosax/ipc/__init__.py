# SPDX-License-Identifier: Apache-2.0
"""kosax.ipc — IPC frame schema and stdio transport for the TUI ↔ backend bridge.

Public surface::

    from kosax.ipc import IPCFrame, run_stdio_loop, write_frame
    from kosax.ipc import (
        UserInputFrame, AssistantChunkFrame, ToolCallFrame, ToolResultFrame,
        CoordinatorPhaseFrame, WorkerStatusFrame, PermissionRequestFrame,
        PermissionResponseFrame, SessionEventFrame, ErrorFrame,
    )
"""

from kosax.ipc.frame_schema import (
    AssistantChunkFrame,
    CoordinatorPhaseFrame,
    ErrorFrame,
    IPCFrame,
    PermissionRequestFrame,
    PermissionResponseFrame,
    SessionEventFrame,
    ToolCallFrame,
    ToolResultEnvelope,
    ToolResultFrame,
    UserInputFrame,
    WorkerStatusFrame,
    ipc_frame_json_schema,
)
from kosax.ipc.stdio import run as run_stdio_loop
from kosax.ipc.stdio import write_frame

__all__ = [
    "IPCFrame",
    "UserInputFrame",
    "AssistantChunkFrame",
    "ToolCallFrame",
    "ToolResultFrame",
    "ToolResultEnvelope",
    "CoordinatorPhaseFrame",
    "WorkerStatusFrame",
    "PermissionRequestFrame",
    "PermissionResponseFrame",
    "SessionEventFrame",
    "ErrorFrame",
    "ipc_frame_json_schema",
    "run_stdio_loop",
    "write_frame",
]
