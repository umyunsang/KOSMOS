# SPDX-License-Identifier: Apache-2.0
"""kosmos.ipc — IPC frame schema and stdio transport for the TUI ↔ backend bridge.

Public surface::

    from kosmos.ipc import IPCFrame, run_stdio_loop, write_frame
    from kosmos.ipc import (
        UserInputFrame, AssistantChunkFrame, ToolCallFrame, ToolResultFrame,
        CoordinatorPhaseFrame, WorkerStatusFrame, PermissionRequestFrame,
        PermissionResponseFrame, SessionEventFrame, ErrorFrame,
    )
"""

from kosmos.ipc.frame_schema import (
    AssistantChunkFrame,
    CoordinatorPhaseFrame,
    ErrorFrame,
    IPCFrame,
    PermissionRequestFrame,
    PermissionResponseFrame,
    SessionEventFrame,
    ToolCallFrame,
    ToolResultFrame,
    ToolResultEnvelope,
    UserInputFrame,
    WorkerStatusFrame,
    ipc_frame_json_schema,
)
from kosmos.ipc.stdio import run as run_stdio_loop, write_frame

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
