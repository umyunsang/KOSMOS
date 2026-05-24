// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — LocatePrimitive prompt strings.

export const LOCATE_TOOL_NAME = 'locate'

/** Citizen-facing English description shown to the LLM. */
export const DESCRIPTION =
  'Invoke one concrete Korean location adapter. Use the function named locate, but set tool_id to a listed locate adapter id from <available_adapters>, never to locate/find/check/send.'

/** Extended prompt included in the system-prompt tool-use section. */
export const LOCATE_TOOL_PROMPT = `Resolve a Korean location phrase into structured location identifiers.

Input:
  { tool_id: string, params: object }

Rules:
- The function name is locate. The tool_id argument is NOT the function name.
- tool_id must be a concrete locate adapter id listed in <available_adapters>, for example "kakao_address_search" or "kakao_coord_to_region".
- Never set tool_id to a root primitive name: "locate", "find", "check", or "send".
- Invalid: locate({ tool_id: "locate", params: {...} })
- Valid:   locate({ tool_id: "kakao_address_search", params: { query: "부산 사하구 다대1동" } })
- Pick tool_id only from <available_adapters> entries whose primitive is locate.
- Use kakao_keyword_search for named places, campuses, stations, landmarks, hospitals, and POIs.
- Coordinate-producing locate results may include KMA nx/ny; pass those exact values to KMA weather adapters that require nx and ny.
- Use kakao_address_search or juso_adm_cd_lookup for structured road/jibun addresses and district text.
- Use kakao_coord_to_region after a coordinate result when a downstream adapter needs q0/q1 or region names.
- If the result is kind="error", do not invent coordinates or administrative codes.`
