# SPDX-License-Identifier: Apache-2.0
"""Degradation message builder for data.go.kr API errors.

Produces Korean-language user-facing messages for common error scenarios.
All message templates use ``name_ko`` from the GovAPITool definition.
"""

from __future__ import annotations

from kosmos.recovery.classifier import ClassifiedError, ErrorClass
from kosmos.tools.models import GovAPITool


def build_degradation_message(tool: GovAPITool, error: ClassifiedError) -> str:
    """Build a Korean-language degradation message for a tool error.

    Args:
        tool: The GovAPITool whose call failed.
        error: The classified error from the recovery pipeline.

    Returns:
        A human-readable Korean string suitable for display to the end user.
    """
    name = tool.name_ko

    if error.error_class == ErrorClass.DEPRECATED:
        return f"{name} 서비스가 종료되었거나 변경되었습니다."

    if error.error_class == ErrorClass.AUTH_FAILURE:
        return f"{name} 서비스 인증이 만료되었습니다. 관리자에게 문의해주세요."

    # Circuit-open is detected via error.source == "circuit_open", set by
    # RecoveryExecutor when the circuit breaker is OPEN.
    if error.source == "circuit_open":
        return f"{name} 서비스가 현재 점검 중이거나 일시적으로 중단되었습니다."

    return f"{name} 서비스 응답 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
