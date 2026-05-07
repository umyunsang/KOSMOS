# SPDX-License-Identifier: Apache-2.0
"""MOHW SSIS enum short reference constants for v4 llm_description section 3.

Source: /tmp/ummaya-domain-docs/mohw_codes.txt § 코드표 (생애주기)
7 life-stage enum codes for the MOHW welfare eligibility search API (lifeArray wire param).
Source: /tmp/ummaya-domain-docs/mohw_codes.txt § 코드표 (가구상황)
6 target-household enum codes for the MOHW welfare eligibility search API
(trgterIndvdlArray wire param).

Format: "001=영유아 / 002=아동 ..." — compact inline table ≤ 80 tokens.
"""

from __future__ import annotations

# MOHW_LIFE_STAGE_SHORT_REFERENCE: 7 life-stage enum → MOHW wire code.
#
# Source: mohw_codes.txt § 코드표 (생애주기)
# Wire param name: lifeArray (camelCase; LLM input field name: life_array → snake_case)
#
#   001 = 영유아   (infants and toddlers, 0-6세)
#   002 = 아동     (children, 7-12세)
#   003 = 청소년   (youth, 13-18세)
#   004 = 청년     (young adults, 19-34세)
#   005 = 중장년   (middle-aged, 35-64세)
#   006 = 노년     (elderly, 65세+)
#   007 = 임신·출산 (pregnancy and childbirth)
MOHW_LIFE_STAGE_SHORT_REFERENCE: str = (
    "001=영유아 / 002=아동 / 003=청소년 / 004=청년 / 005=중장년 / 006=노년 / 007=임신·출산"
)

# MOHW_TARGET_HOUSEHOLD_SHORT_REFERENCE: 6 target-household enum → MOHW wire code.
#
# Source: mohw_codes.txt § 코드표 (가구상황)
# Wire param name: trgterIndvdlArray
# LLM input field name: trgter_indvdl_array → snake_case
MOHW_TARGET_HOUSEHOLD_SHORT_REFERENCE: str = (
    "010=다문화·탈북민 / 020=다자녀 / 030=보훈 / 040=장애인 / 050=저소득 / 060=한부모·조손"
)
