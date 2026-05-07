// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — ResolveLocationPrimitive prompt strings.

export const RESOLVE_LOCATION_TOOL_NAME = 'resolve_location'

/** Citizen-facing Korean description shown to the LLM. */
export const DESCRIPTION =
  '한국 위치 표현을 좌표, 법정동 코드, 주소, 지역명으로 해석합니다. 후속 공공서비스 어댑터가 lat/lon, adm_cd, b_code, region을 요구할 때 먼저 호출하세요.'

/** Extended prompt included in the system-prompt tool-use section. */
export const RESOLVE_LOCATION_TOOL_PROMPT = `Resolve a Korean location phrase into structured location identifiers.

Input:
  { query: string, want?: "coords" | "adm_cd" | "coords_and_admcd" | "road_address" | "jibun_address" | "poi" | "region" | "all", near?: [lat, lon] }

Rules:
- Use this before lookup/submit adapters that require coordinates, b_code, adm_cd, or region text.
- Preserve the citizen's location phrase in query.
- Use want="coords_and_admcd" unless a downstream adapter asks for only one identifier.
- If the result is kind="error", do not invent coordinates or administrative codes.`
