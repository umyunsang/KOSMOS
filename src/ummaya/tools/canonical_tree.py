# SPDX-License-Identifier: Apache-2.0
"""Canonical tool-system tree paths.

The canonical adapter hierarchy is:

    primitive / agency / agency_service / adapter

Existing implementation modules may keep compatibility import paths during
migration, but registry-facing metadata and audits use this tree as the single
ownership model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from ummaya.tools.models import GovAPITool

PrimitiveName = Literal["find", "locate", "check", "send"]

_ROOT_PRIMITIVES = frozenset({"find", "locate", "check", "send"})

_SPECIAL_AGENCIES: dict[str, str] = {
    "mock_kftc_opengiro_bill_send_v1": "kftc",
    "mock_kftc_opengiro_payment_send_v1": "kftc",
    "mock_submit_module_gov24_minwon": "gov24",
    "mock_submit_module_hometax_taxreturn": "hometax",
    "mock_submit_module_public_mydata_action": "mydata",
    "mock_traffic_fine_pay_v1": "koroad",
    "mock_welfare_application_submit_v1": "mohw",
    "mock_verify_ganpyeon_injeung": "kftc",
    "mock_verify_geumyung_injeungseo": "kftc",
    "mock_verify_gongdong_injeungseo": "rootca",
    "mock_verify_mobile_id": "mobile_id",
    "mock_verify_module_any_id_sso": "any_id",
    "mock_verify_module_geumyung": "kftc",
    "mock_verify_module_kec": "kec",
    "mock_verify_module_modid": "mobile_id",
    "mock_verify_module_simple_auth": "kftc",
    "mock_verify_mydata": "mydata",
}

_SPECIAL_SERVICES: dict[str, str] = {
    "find": "core",
    "locate": "core",
    "check": "core",
    "send": "core",
    "kakao_address_search": "kakao_local",
    "kakao_keyword_search": "kakao_local",
    "kakao_coord_to_region": "kakao_local",
    "juso_adm_cd_lookup": "juso_addr_link",
    "sgis_adm_cd_lookup": "sgis_reverse_geocode",
    "kma_current_observation": "vilage_fcst_info_service_2_0",
    "kma_forecast_fetch": "vilage_fcst_info_service_2_0",
    "kma_short_term_forecast": "vilage_fcst_info_service_2_0",
    "kma_ultra_short_term_forecast": "vilage_fcst_info_service_2_0",
    "kma_pre_warning": "wthr_wrn_info_service",
    "kma_weather_alert_status": "wthr_wrn_info_service",
    "mock_kftc_opengiro_bill_send_v1": "opengiro",
    "mock_kftc_opengiro_payment_send_v1": "opengiro",
    "mock_submit_module_gov24_minwon": "minwon",
    "mock_submit_module_hometax_taxreturn": "taxreturn",
    "mock_submit_module_public_mydata_action": "public_mydata",
    "mock_traffic_fine_pay_v1": "traffic_fine",
    "mock_welfare_application_submit_v1": "welfare_application",
}


@dataclass(frozen=True, slots=True)
class ToolTreePath:
    """Primitive -> agency -> service -> adapter path for one registered tool."""

    primitive: PrimitiveName
    agency: str
    service: str
    adapter: str

    @property
    def parts(self) -> tuple[str, str, str, str]:
        """Return path parts in canonical order."""

        return (self.primitive, self.agency, self.service, self.adapter)

    @property
    def package_path(self) -> str:
        """Return the Python-package-shaped canonical path suffix."""

        return "/".join(self.parts)


def canonical_tool_tree_path(tool: GovAPITool) -> ToolTreePath:
    """Return the canonical ownership path for a registered tool."""

    primitive = _primitive(tool)
    return ToolTreePath(
        primitive=primitive,
        agency=_agency_slug(tool),
        service=_service_slug(tool),
        adapter=_slug(tool.id),
    )


def _primitive(tool: GovAPITool) -> PrimitiveName:
    raw = tool.primitive or "find"
    if raw in ("find", "locate", "check", "send"):
        return raw
    return "find"


def _agency_slug(tool: GovAPITool) -> str:
    if tool.id in _ROOT_PRIMITIVES:
        return "ummaya"
    if tool.id in _SPECIAL_AGENCIES:
        return _SPECIAL_AGENCIES[tool.id]
    return _slug(tool.ministry)


def _service_slug(tool: GovAPITool) -> str:
    if tool.id in _SPECIAL_SERVICES:
        return _SPECIAL_SERVICES[tool.id]
    if tool.id.startswith("kma_apihub_"):
        return _kma_apihub_service_slug(tool.id)
    if tool.id.startswith("mock_verify_"):
        return "verify"
    if tool.id.startswith("mock_lookup_"):
        return "lookup"
    if tool.id.startswith("mock_submit_"):
        return "submit"

    spec_service = _verified_spec_service(tool.id)
    if spec_service:
        return spec_service

    return _generic_service_slug(tool.id, _agency_slug(tool))


def _kma_apihub_service_slug(tool_id: str) -> str:
    rest = tool_id.removeprefix("kma_apihub_")
    match = re.match(r"(?P<service>.+?)_(get|post|put|delete)r?_", rest)
    if match:
        return _slug(match.group("service"))
    return _slug(rest)


def _verified_spec_service(tool_id: str) -> str | None:
    try:
        from ummaya.tools.verified_data_go_kr._manifest import require_spec  # noqa: PLC0415
    except ImportError:
        return None
    try:
        spec = require_spec(tool_id)
    except KeyError:
        return None
    return _slug(spec.module_name)


def _generic_service_slug(tool_id: str, agency_slug: str) -> str:
    service = tool_id
    if service.startswith(f"{agency_slug}_"):
        service = service.removeprefix(f"{agency_slug}_")
    for suffix in (
        "_search",
        "_lookup",
        "_fetch",
        "_check",
        "_status",
        "_service",
        "_submit",
        "_locate",
    ):
        service = service.removesuffix(suffix)
    return _slug(service)


def _slug(value: str) -> str:
    slug = value.lower().replace("-", "_").replace(".", "_")
    slug = re.sub(r"[^a-z0-9_]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"
