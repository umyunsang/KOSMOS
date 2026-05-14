// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — LocatePrimitive prompt strings.

export const LOCATE_TOOL_NAME = 'locate'

/** Citizen-facing English description shown to the LLM. */
export const DESCRIPTION =
  'Invoke a locate adapter for Korean location expressions. Choose a Kakao, JUSO, or SGIS adapter from <available_adapters> and fill params from its input_schema.'

/** Extended prompt included in the system-prompt tool-use section. */
export const LOCATE_TOOL_PROMPT = `Resolve a Korean location phrase into structured location identifiers.

Input:
  { tool_id: string, params: object }

Rules:
- Pick tool_id only from <available_adapters> entries whose primitive is locate.
- Use kakao_keyword_search for named places, campuses, stations, landmarks, hospitals, and POIs.
- Coordinate-producing locate results may include KMA nx/ny; pass those exact values to KMA weather adapters that require nx and ny.
- Use kakao_address_search or juso_adm_cd_lookup for structured road/jibun addresses and district text.
- Use kakao_coord_to_region after a coordinate result when a downstream adapter needs q0/q1 or region names.
- If the result is kind="error", do not invent coordinates or administrative codes.`
