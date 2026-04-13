# SPDX-License-Identifier: Apache-2.0
"""Error classifier for data.go.kr API responses.

Translates raw HTTP status codes, response bodies, and exceptions into
a normalized ``ClassifiedError`` for the recovery pipeline.

NFR-006: No XML parser dependency — gateway XML errors are detected with
plain string operations only.
"""

from __future__ import annotations

import json
import logging
from enum import IntEnum, StrEnum

import httpx
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class DataGoKrErrorCode(IntEnum):
    """Numeric return codes used by the data.go.kr Open API gateway."""

    NORMAL_CODE = 0
    APPLICATION_ERROR = 1
    DB_ERROR = 2
    NO_DATA = 3
    HTTP_ERROR = 4
    SERVICE_TIMEOUT = 5
    INVALID_REQUEST_PARAMETER = 10
    NO_REQUIRED_REQUEST_PARAMETER = 11
    SERVICE_NOT_FOUND = 20
    TEMPORARILY_DISABLED = 22
    LIMIT_NUMBER_OF_SERVICE_REQUESTS_EXCEEDED = 30
    SERVICE_KEY_NOT_REGISTERED = 31
    DEADLINE_HAS_EXPIRED = 32
    UNREGISTERED_IP = 33
    UNKNOWN_ERROR = 99


class ErrorClass(StrEnum):
    """Normalized error classification for the recovery pipeline."""

    TRANSIENT = "transient"
    """Temporary server-side failure; safe to retry."""

    RATE_LIMIT = "rate_limit"
    """Request quota exceeded; retry after back-off."""

    AUTH_FAILURE = "auth_failure"
    """Authentication/authorization failure; do not retry."""

    DATA_MISSING = "data_missing"
    """No data available for the request parameters; do not retry."""

    INVALID_REQUEST = "invalid_request"
    """Bad request parameters; do not retry."""

    TIMEOUT = "timeout"
    """Network or service timeout; safe to retry."""

    DEPRECATED = "deprecated"
    """Service has been removed or moved; do not retry."""

    APP_ERROR = "app_error"
    """Application-level error; do not retry."""

    UNKNOWN = "unknown"
    """Unrecognized error; do not retry (fail-closed)."""


# ---------------------------------------------------------------------------
# Retryable error classes
# ---------------------------------------------------------------------------

_RETRYABLE: frozenset[ErrorClass] = frozenset(
    {ErrorClass.TRANSIENT, ErrorClass.RATE_LIMIT, ErrorClass.TIMEOUT}
)

# ---------------------------------------------------------------------------
# Mapping from DataGoKrErrorCode → ErrorClass
# ---------------------------------------------------------------------------

_CODE_TO_CLASS: dict[int, ErrorClass] = {
    DataGoKrErrorCode.NORMAL_CODE: ErrorClass.UNKNOWN,  # should not appear on failure path
    DataGoKrErrorCode.APPLICATION_ERROR: ErrorClass.APP_ERROR,
    DataGoKrErrorCode.DB_ERROR: ErrorClass.TRANSIENT,
    DataGoKrErrorCode.NO_DATA: ErrorClass.DATA_MISSING,
    DataGoKrErrorCode.HTTP_ERROR: ErrorClass.TRANSIENT,
    DataGoKrErrorCode.SERVICE_TIMEOUT: ErrorClass.TRANSIENT,
    DataGoKrErrorCode.INVALID_REQUEST_PARAMETER: ErrorClass.INVALID_REQUEST,
    DataGoKrErrorCode.NO_REQUIRED_REQUEST_PARAMETER: ErrorClass.INVALID_REQUEST,
    DataGoKrErrorCode.SERVICE_NOT_FOUND: ErrorClass.DEPRECATED,
    DataGoKrErrorCode.TEMPORARILY_DISABLED: ErrorClass.DEPRECATED,
    DataGoKrErrorCode.LIMIT_NUMBER_OF_SERVICE_REQUESTS_EXCEEDED: ErrorClass.RATE_LIMIT,
    DataGoKrErrorCode.SERVICE_KEY_NOT_REGISTERED: ErrorClass.AUTH_FAILURE,
    DataGoKrErrorCode.DEADLINE_HAS_EXPIRED: ErrorClass.AUTH_FAILURE,
    DataGoKrErrorCode.UNREGISTERED_IP: ErrorClass.AUTH_FAILURE,
    DataGoKrErrorCode.UNKNOWN_ERROR: ErrorClass.UNKNOWN,
}


class ClassifiedError(BaseModel):
    """Normalized representation of a classified API error."""

    model_config = ConfigDict(frozen=True)

    error_class: ErrorClass
    """High-level error category."""

    is_retryable: bool
    """Whether the recovery pipeline should retry this error."""

    raw_code: int | None = None
    """Original numeric error code from the gateway, if available."""

    raw_message: str = ""
    """Human-readable error description from the source."""

    source: str = ""
    """Origin of the error (e.g. ``"data_go_kr_xml"``, ``"data_go_kr_json"``,
    ``"http_status"``, ``"transport"``, ``"unknown"``)."""


class DataGoKrErrorClassifier:
    """Classify errors from data.go.kr API responses and Python exceptions.

    The classifier is stateless and all methods are pure functions; it is safe
    to reuse a single instance across concurrent coroutines.
    """

    # XML gateway response prefix (NFR-006: string-only, no XML parser)
    _XML_GATEWAY_PREFIX: str = "<OpenAPI_ServiceResponse>"

    # XML tag markers for code extraction
    _XML_CODE_START: str = "<returnReasonCode>"
    _XML_CODE_END: str = "</returnReasonCode>"
    _XML_MSG_START: str = "<returnAuthMsg>"
    _XML_MSG_END: str = "</returnAuthMsg>"

    def classify_response(
        self,
        status_code: int,
        body: str,
        content_type: str | None = None,
    ) -> ClassifiedError:
        """Classify an HTTP response from the data.go.kr gateway.

        Detection order:
        1. XML gateway error (HTTP 200 with XML body despite requesting JSON).
        2. JSON ``resultCode`` field.
        3. HTTP status code.

        Args:
            status_code: HTTP response status code.
            body: Response body as a decoded string.
            content_type: Value of the Content-Type header (may be None or empty).

        Returns:
            A ``ClassifiedError`` describing the error class and retryability.
        """
        # --- 1. XML gateway detection (NFR-006: no XML parser) ---
        if body.startswith(self._XML_GATEWAY_PREFIX):
            return self._classify_xml_gateway(body)

        # --- 2. JSON body with resultCode ---
        if "resultCode" in body:
            try:
                parsed = json.loads(body)
                result_code = self._extract_result_code(parsed)
                if result_code is not None:
                    result_msg = self._extract_result_msg(parsed)
                    return self._classify_by_code(
                        result_code, result_msg, source="data_go_kr_json"
                    )
            except (json.JSONDecodeError, TypeError, KeyError, ValueError):
                logger.debug("Failed to parse JSON body for error classification")

        # --- 3. HTTP status code fallback ---
        return self._classify_by_http_status(status_code, body)

    def classify_exception(self, exc: Exception) -> ClassifiedError:
        """Classify a Python exception raised during an API call.

        Args:
            exc: The exception to classify.

        Returns:
            A ``ClassifiedError`` describing the error class and retryability.
        """
        if isinstance(exc, (httpx.ConnectTimeout, httpx.ReadTimeout)):
            return ClassifiedError(
                error_class=ErrorClass.TIMEOUT,
                is_retryable=True,
                raw_code=None,
                raw_message=str(exc),
                source="transport",
            )

        if isinstance(exc, httpx.TimeoutException):
            return ClassifiedError(
                error_class=ErrorClass.TIMEOUT,
                is_retryable=True,
                raw_code=None,
                raw_message=str(exc),
                source="transport",
            )

        if isinstance(exc, httpx.HTTPStatusError):
            try:
                content_type = exc.response.headers.get("content-type")
                return self.classify_response(
                    exc.response.status_code,
                    exc.response.text,
                    content_type,
                )
            except Exception:  # noqa: BLE001
                return self._classify_by_http_status(exc.response.status_code, str(exc))

        return ClassifiedError(
            error_class=ErrorClass.APP_ERROR,
            is_retryable=False,
            raw_code=None,
            raw_message=str(exc),
            source="unknown",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _classify_xml_gateway(self, body: str) -> ClassifiedError:
        """Extract return code from an XML gateway response without a parser."""
        raw_code: int | None = None
        raw_message: str = "XML gateway error"

        code_start = body.find(self._XML_CODE_START)
        if code_start != -1:
            code_start += len(self._XML_CODE_START)
            code_end = body.find(self._XML_CODE_END, code_start)
            if code_end != -1:
                code_str = body[code_start:code_end].strip()
                try:
                    raw_code = int(code_str)
                except ValueError:
                    logger.debug("Could not parse XML gateway returnReasonCode: %r", code_str)

        msg_start = body.find(self._XML_MSG_START)
        if msg_start != -1:
            msg_start += len(self._XML_MSG_START)
            msg_end = body.find(self._XML_MSG_END, msg_start)
            if msg_end != -1:
                raw_message = body[msg_start:msg_end].strip()

        if raw_code is not None:
            return self._classify_by_code(raw_code, raw_message, source="data_go_kr_xml")

        return ClassifiedError(
            error_class=ErrorClass.UNKNOWN,
            is_retryable=False,
            raw_code=None,
            raw_message=raw_message,
            source="data_go_kr_xml",
        )

    def _extract_result_msg(self, parsed: object) -> str:
        """Recursively find resultMsg in nested JSON structures.

        Returns the message string, or an empty string if not found.
        """
        if isinstance(parsed, dict):
            if "resultMsg" in parsed:
                return str(parsed["resultMsg"])
            for key in ("response", "header", "OpenAPI_ServiceResponse"):
                if key in parsed:
                    result = self._extract_result_msg(parsed[key])
                    if result:
                        return result
        return ""

    def _extract_result_code(self, parsed: object) -> int | None:
        """Recursively find resultCode in nested JSON structures."""
        if isinstance(parsed, dict):
            if "resultCode" in parsed:
                val = parsed["resultCode"]
                if isinstance(val, int):
                    return val
                if isinstance(val, str) and val.isdigit():
                    return int(val)
            # Try nested structures (data.go.kr wraps in response/header)
            for key in ("response", "header", "OpenAPI_ServiceResponse"):
                if key in parsed:
                    result = self._extract_result_code(parsed[key])
                    if result is not None:
                        return result
        return None

    def _classify_by_code(self, code: int, message: str, *, source: str) -> ClassifiedError:
        """Map a numeric gateway code to an ErrorClass."""
        error_class = _CODE_TO_CLASS.get(code, ErrorClass.UNKNOWN)
        return ClassifiedError(
            error_class=error_class,
            is_retryable=error_class in _RETRYABLE,
            raw_code=code,
            raw_message=message,
            source=source,
        )

    def _classify_by_http_status(self, status_code: int, message: str) -> ClassifiedError:
        """Classify based purely on HTTP status code."""
        if status_code == 429:
            error_class = ErrorClass.RATE_LIMIT
        elif status_code in (401, 403):
            error_class = ErrorClass.AUTH_FAILURE
        elif status_code in (502, 503, 504):
            error_class = ErrorClass.TRANSIENT
        elif status_code == 400:
            error_class = ErrorClass.INVALID_REQUEST
        elif status_code == 404:
            error_class = ErrorClass.DATA_MISSING
        elif status_code == 500:
            error_class = ErrorClass.APP_ERROR
        else:
            error_class = ErrorClass.UNKNOWN

        return ClassifiedError(
            error_class=error_class,
            is_retryable=error_class in _RETRYABLE,
            raw_code=status_code,
            raw_message=message,
            source="http_status",
        )
