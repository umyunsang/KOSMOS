# SPDX-License-Identifier: Apache-2.0
"""Tests for the DataGoKrErrorClassifier and related models."""

from __future__ import annotations

import json

import httpx
import pytest

from kosmos.recovery.classifier import (
    ClassifiedError,
    DataGoKrErrorClassifier,
    DataGoKrErrorCode,
    ErrorClass,
)


@pytest.fixture()
def classifier() -> DataGoKrErrorClassifier:
    return DataGoKrErrorClassifier()


# ---------------------------------------------------------------------------
# ErrorCode mapping tests
# ---------------------------------------------------------------------------


class TestDataGoKrErrorCodes:
    def test_all_codes_defined(self) -> None:
        """All 15 error codes specified in the design are present."""
        expected_codes = {0, 1, 2, 3, 4, 5, 10, 11, 20, 22, 30, 31, 32, 33, 99}
        actual_codes = {int(c) for c in DataGoKrErrorCode}
        assert expected_codes == actual_codes

    def test_code_values(self) -> None:
        assert DataGoKrErrorCode.NORMAL_CODE == 0
        assert DataGoKrErrorCode.APPLICATION_ERROR == 1
        assert DataGoKrErrorCode.DB_ERROR == 2
        assert DataGoKrErrorCode.NO_DATA == 3
        assert DataGoKrErrorCode.HTTP_ERROR == 4
        assert DataGoKrErrorCode.SERVICE_TIMEOUT == 5
        assert DataGoKrErrorCode.INVALID_REQUEST_PARAMETER == 10
        assert DataGoKrErrorCode.NO_REQUIRED_REQUEST_PARAMETER == 11
        assert DataGoKrErrorCode.SERVICE_NOT_FOUND == 20
        assert DataGoKrErrorCode.TEMPORARILY_DISABLED == 22
        assert DataGoKrErrorCode.LIMIT_NUMBER_OF_SERVICE_REQUESTS_EXCEEDED == 30
        assert DataGoKrErrorCode.SERVICE_KEY_NOT_REGISTERED == 31
        assert DataGoKrErrorCode.DEADLINE_HAS_EXPIRED == 32
        assert DataGoKrErrorCode.UNREGISTERED_IP == 33
        assert DataGoKrErrorCode.UNKNOWN_ERROR == 99


# ---------------------------------------------------------------------------
# XML gateway detection via sample_xml_gateway_response fixture
# ---------------------------------------------------------------------------


class TestXmlGatewayDetection:
    def test_xml_gateway_with_code_30(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(30, "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.RATE_LIMIT
        assert result.is_retryable is True
        assert result.raw_code == 30
        assert result.source == "data_go_kr_xml"

    def test_xml_gateway_with_code_31(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(31, "SERVICE_KEY_NOT_REGISTERED_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.AUTH_FAILURE
        assert result.is_retryable is False
        assert result.raw_code == 31
        assert result.source == "data_go_kr_xml"

    def test_xml_gateway_with_code_32(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(32, "DEADLINE_EXPIRED")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.AUTH_FAILURE
        assert result.raw_code == 32

    def test_xml_gateway_with_code_33(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(33, "UNREGISTERED_IP")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.AUTH_FAILURE
        assert result.raw_code == 33

    def test_xml_gateway_code_2_transient(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(2, "DB_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.TRANSIENT
        assert result.is_retryable is True

    def test_xml_gateway_code_3_data_missing(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(3, "NO_DATA")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.DATA_MISSING
        assert result.is_retryable is False

    def test_xml_gateway_code_10_invalid_request(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(10, "INVALID_REQUEST_PARAMETER")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.INVALID_REQUEST
        assert result.is_retryable is False

    def test_xml_gateway_code_20_deprecated(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(20, "SERVICE_NOT_FOUND")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.DEPRECATED

    def test_xml_gateway_code_99_unknown(
        self, classifier: DataGoKrErrorClassifier, sample_xml_gateway_response: object
    ) -> None:
        body = sample_xml_gateway_response(99, "UNKNOWN_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.UNKNOWN
        assert result.is_retryable is False

    def test_xml_gateway_without_code(self, classifier: DataGoKrErrorClassifier) -> None:
        body = (
            "<OpenAPI_ServiceResponse>"
            "<returnAuthMsg>Unknown</returnAuthMsg>"
            "</OpenAPI_ServiceResponse>"
        )
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.UNKNOWN
        assert result.raw_code is None
        assert result.source == "data_go_kr_xml"

    def test_non_xml_body_not_treated_as_xml(self, classifier: DataGoKrErrorClassifier) -> None:
        body = '{"resultCode": 0, "resultMsg": "NORMAL SERVICE."}'
        result = classifier.classify_response(200, body)
        # Should NOT trigger xml gateway path
        assert result.source != "data_go_kr_xml"

    def test_xml_gateway_prefix_detection(self, classifier: DataGoKrErrorClassifier) -> None:
        """Verify <OpenAPI_ServiceResponse> prefix triggers XML gateway path."""
        body = (
            "<OpenAPI_ServiceResponse>"
            "<returnReasonCode>30</returnReasonCode>"
            "</OpenAPI_ServiceResponse>"
        )
        result = classifier.classify_response(200, body)
        assert result.source == "data_go_kr_xml"


# ---------------------------------------------------------------------------
# JSON body classification via sample_json_error_response fixture
# ---------------------------------------------------------------------------


class TestJsonBodyClassification:
    def test_code_0_normal_maps_to_unknown(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(0, "NORMAL SERVICE.")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.UNKNOWN  # code 0 on failure path = unknown
        assert result.raw_code == 0

    def test_code_1_application_error(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(1, "APPLICATION_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.APP_ERROR
        assert result.is_retryable is False

    def test_code_2_db_error_is_transient(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(2, "DB_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.TRANSIENT
        assert result.is_retryable is True

    def test_code_3_no_data(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(3, "NO_DATA")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.DATA_MISSING
        assert result.is_retryable is False

    def test_code_4_http_error_is_transient(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(4, "HTTP_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.TRANSIENT

    def test_code_5_service_timeout_is_transient(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(5, "SERVICE_TIMEOUT")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.TRANSIENT

    def test_code_10_invalid_param(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(10, "INVALID_REQUEST_PARAMETER")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.INVALID_REQUEST
        assert result.is_retryable is False

    def test_code_11_missing_param(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(11, "NO_REQUIRED_REQUEST_PARAMETER")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.INVALID_REQUEST

    def test_code_20_service_not_found(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(20, "SERVICE_NOT_FOUND")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.DEPRECATED

    def test_code_22_temporarily_disabled(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(22, "TEMPORARILY_DISABLED")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.DEPRECATED

    def test_code_30_rate_limit(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(30, "LIMIT_EXCEEDED")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.RATE_LIMIT
        assert result.is_retryable is True

    def test_code_31_key_not_registered(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(31, "SERVICE_KEY_NOT_REGISTERED")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.AUTH_FAILURE

    def test_code_99_unknown(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(99, "UNKNOWN_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.UNKNOWN
        assert result.is_retryable is False

    def test_unknown_result_code(self, classifier: DataGoKrErrorClassifier) -> None:
        """Unknown resultCode should map to UNKNOWN with is_retryable=False."""
        body = json.dumps({"resultCode": 777, "resultMsg": "unexpected"})
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.UNKNOWN
        assert result.is_retryable is False

    def test_string_result_code(self, classifier: DataGoKrErrorClassifier) -> None:
        body = json.dumps({"resultCode": "30"})
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.RATE_LIMIT

    def test_json_source_label(
        self, classifier: DataGoKrErrorClassifier, sample_json_error_response: object
    ) -> None:
        body = sample_json_error_response(1, "APP_ERROR")  # type: ignore[operator]
        result = classifier.classify_response(200, body)
        assert result.source == "data_go_kr_json"


# ---------------------------------------------------------------------------
# HTTP status classification
# ---------------------------------------------------------------------------


class TestHttpStatusClassification:
    def test_429_rate_limit(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(429, "Too Many Requests")
        assert result.error_class == ErrorClass.RATE_LIMIT
        assert result.is_retryable is True
        assert result.source == "http_status"

    def test_401_auth_failure(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(401, "Unauthorized")
        assert result.error_class == ErrorClass.AUTH_FAILURE
        assert result.is_retryable is False

    def test_403_auth_failure(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(403, "Forbidden")
        assert result.error_class == ErrorClass.AUTH_FAILURE

    def test_502_transient(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(502, "Bad Gateway")
        assert result.error_class == ErrorClass.TRANSIENT
        assert result.is_retryable is True

    def test_503_transient(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(503, "Service Unavailable")
        assert result.error_class == ErrorClass.TRANSIENT

    def test_504_transient(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(504, "Gateway Timeout")
        assert result.error_class == ErrorClass.TRANSIENT

    def test_400_invalid_request(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(400, "Bad Request")
        assert result.error_class == ErrorClass.INVALID_REQUEST
        assert result.is_retryable is False
        assert result.source == "http_status"

    def test_404_data_missing(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(404, "Not Found")
        assert result.error_class == ErrorClass.DATA_MISSING
        assert result.is_retryable is False
        assert result.source == "http_status"

    def test_500_app_error(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(500, "Internal Server Error")
        assert result.error_class == ErrorClass.APP_ERROR
        assert result.is_retryable is False
        assert result.source == "http_status"

    def test_other_4xx_unknown(self, classifier: DataGoKrErrorClassifier) -> None:
        result = classifier.classify_response(418, "I'm a teapot")
        assert result.error_class == ErrorClass.UNKNOWN
        assert result.is_retryable is False

    def test_empty_body(self, classifier: DataGoKrErrorClassifier) -> None:
        """Empty response body with non-special status falls back to HTTP status."""
        result = classifier.classify_response(500, "")
        assert result.error_class == ErrorClass.APP_ERROR
        assert result.is_retryable is False


# ---------------------------------------------------------------------------
# Exception classification
# ---------------------------------------------------------------------------


class TestExceptionClassification:
    def test_connect_timeout(self, classifier: DataGoKrErrorClassifier) -> None:
        exc = httpx.ConnectTimeout("connection timed out")
        result = classifier.classify_exception(exc)
        assert result.error_class == ErrorClass.TIMEOUT
        assert result.is_retryable is True
        assert result.source == "transport"

    def test_read_timeout(self, classifier: DataGoKrErrorClassifier) -> None:
        exc = httpx.ReadTimeout("read timed out")
        result = classifier.classify_exception(exc)
        assert result.error_class == ErrorClass.TIMEOUT
        assert result.is_retryable is True
        assert result.source == "transport"

    def test_http_status_error_401(self, classifier: DataGoKrErrorClassifier) -> None:
        request = httpx.Request("GET", "https://api.example.com/")
        response = httpx.Response(401, request=request)
        exc = httpx.HTTPStatusError("401 Unauthorized", request=request, response=response)
        result = classifier.classify_exception(exc)
        assert result.error_class == ErrorClass.AUTH_FAILURE
        assert result.is_retryable is False

    def test_http_status_error_503(self, classifier: DataGoKrErrorClassifier) -> None:
        request = httpx.Request("GET", "https://api.example.com/")
        response = httpx.Response(503, request=request)
        exc = httpx.HTTPStatusError("503 Service Unavailable", request=request, response=response)
        result = classifier.classify_exception(exc)
        assert result.error_class == ErrorClass.TRANSIENT
        assert result.is_retryable is True

    def test_generic_exception_app_error(self, classifier: DataGoKrErrorClassifier) -> None:
        exc = ValueError("something went wrong")
        result = classifier.classify_exception(exc)
        assert result.error_class == ErrorClass.APP_ERROR
        assert result.is_retryable is False
        assert result.source == "unknown"

    def test_non_httpx_exception(self, classifier: DataGoKrErrorClassifier) -> None:
        """Any non-httpx exception should be classified as APP_ERROR with source=unknown."""
        exc = RuntimeError("crash")
        result = classifier.classify_exception(exc)
        assert result.error_class == ErrorClass.APP_ERROR
        assert result.is_retryable is False
        assert result.source == "unknown"


# ---------------------------------------------------------------------------
# ClassifiedError model
# ---------------------------------------------------------------------------


class TestClassifiedError:
    def test_frozen(self) -> None:
        err = ClassifiedError(
            error_class=ErrorClass.TRANSIENT,
            is_retryable=True,
            raw_code=5,
            raw_message="timeout",
            source="data_go_kr_json",
        )
        with pytest.raises(Exception):  # noqa: B017
            err.error_class = ErrorClass.UNKNOWN  # type: ignore[misc]

    def test_defaults_for_optional_fields(self) -> None:
        """raw_message and source have empty string defaults."""
        err = ClassifiedError(
            error_class=ErrorClass.UNKNOWN,
            is_retryable=False,
        )
        assert err.raw_message == ""
        assert err.source == ""
        assert err.raw_code is None

    def test_normal_code_handling(self, classifier: DataGoKrErrorClassifier) -> None:
        """Normal code (0) on the failure path should produce UNKNOWN, not retryable."""
        body = json.dumps({"resultCode": 0, "resultMsg": "NORMAL SERVICE."})
        result = classifier.classify_response(200, body)
        assert result.error_class == ErrorClass.UNKNOWN
        assert result.is_retryable is False
