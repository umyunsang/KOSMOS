# CJK Width Known Issues

**Spec**: Spec 287 (KOSMOS TUI — Ink + React + Bun)
**Affects**: `tui/src/components/primitive/TimeseriesTable.tsx`, `tui/src/components/primitive/CollectionList.tsx`, and all other primitive renderers that emit padded columns.
**Cross-reference**: Spec 287 § Assumptions, Assumption #3; Spec 287 § Edge Cases, R5.

---

## Overview

East Asian characters (CJK — Chinese, Japanese, Korean) occupy two terminal columns visually but are counted as one column by JavaScript's `String.prototype.length` and by many early or naive width-calculation libraries. When a renderer computes column padding by counting characters rather than visual columns, CJK text causes columns to misalign, table borders to drift, and row overflow to trigger at the wrong glyph boundary.

This document catalogs the two upstream Ink issues that affect KOSMOS TUI rendering, the mitigation applied in every primitive renderer, and the residual known defect deferred to a future release.

---

## Known Upstream Bugs

### ink#688 — CJK characters miscounted as 1 column

**Source**: [ink#688](https://github.com/vadimdemedes/ink/issues/688)

Ink's internal text-layout pass calls `str.length` to calculate the printable width of a rendered string. For any CJK Unified Ideograph or Hangul syllable block character (U+1100–U+11FF, U+3000–U+9FFF, U+AC00–U+D7A3, U+F900–U+FAFF, and CJK Compatibility ranges), `str.length` returns 1 even though the glyph renders as 2 columns in every conforming terminal emulator (kitty, alacritty, iTerm2, Konsole, GNOME Terminal).

**Reproduction context in KOSMOS TUI**

The defect is most visible in `TimeseriesTable.tsx` (FR-018) and `CollectionList.tsx` (FR-019) because both components construct fixed-width padded columns from backend `tool_result` data that routinely contains Korean text (hospital names, district names, road segment labels). A typical failing row:

```
# Expected (2-col Korean glyphs counted correctly)
| 서울특별시  | 기온   | 25.3°C |

# Actual without mitigation (each Korean glyph counted as 1 col)
| 서울특별시    | 기온     | 25.3°C |
```

With a table of 40 Korean-label rows the border misalignment accumulates into unreadable output.

**Scope**: Affects any Ink component that pads or truncates a string using the raw length property rather than a Unicode-aware width library.

### ink#759 — Zero-width joiner and emoji variation selectors cause width drift

**Source**: [ink#759](https://github.com/vadimdemedes/ink/issues/759)

Zero-width joiner sequences (U+200D, e.g., family emoji ZWJ sequences) and variation selectors (U+FE0E / U+FE0F — text vs. emoji presentation) are assigned a character length of 1 by `str.length` but should contribute 0 to the printable column count. Combined with the ink#688 problem, a single ZWJ emoji in a header label can cause all downstream columns to shift by 1–3 positions.

**Reproduction context in KOSMOS TUI**

`CollectionList.tsx` displays emergency-facility and hospital records from `nmc_emergency_search` and `hira_hospital_search` adapters. Some upstream records include emoji variation selectors in facility-type labels (e.g., status indicators). The variation selector is invisible to the user but counted as 1 by Ink, shifting the following column header.

**Scope**: Affects any renderer that does not strip or correctly measure variation selectors before column padding.

---

## Mitigation

All primitive renderers in `tui/src/components/primitive/*.tsx` MUST compute column widths using `string-width@^7` (declared in `tui/package.json` as a primary dependency; see `specs/287-tui-ink-react-bun/plan.md` § Primary Dependencies).

### Usage contract

Before computing padding for any table cell or list column:

```typescript
import stringWidth from 'string-width';

function padEnd(text: string, targetWidth: number, fillChar = ' '): string {
  const printableWidth = stringWidth(text);
  const padCount = Math.max(0, targetWidth - printableWidth);
  return text + fillChar.repeat(padCount);
}
```

`stringWidth` correctly handles:
- CJK Unified Ideographs and Hangul syllable blocks (2-col return value, resolves ink#688).
- Variation selectors U+FE0E / U+FE0F and zero-width joiners U+200D (0-col return value, partially resolves ink#759 — see Known Limits below).
- Combining diacritical marks common in romanized Korean transliterations.

Every renderer that hard-codes column widths or calls `.padEnd()` / `.padStart()` on user-visible strings is a defect. Use `padEnd()` / a `padStart()` wrapper above in all such call sites.

**Log contract**: When the computed `stringWidth` result differs from `text.length` by more than 0, the renderer MUST emit a `debug`-level log entry via `stdlib logging` (Python side) or the TUI's `KOSMOS_TUI_LOG_LEVEL` channel (TypeScript side) — it MUST NOT throw. This satisfies Spec 287 § Edge Cases R5: "Log a warning on overflow but do not crash."

**Affected files** (to be created in Phase 1–3):

- `tui/src/components/primitive/TimeseriesTable.tsx`
- `tui/src/components/primitive/CollectionList.tsx`
- `tui/src/components/primitive/PointCard.tsx`
- `tui/src/components/primitive/DetailView.tsx`
- `tui/src/components/primitive/EventStream.tsx`
- All remaining files under `tui/src/components/primitive/`

---

## Known Limits (Open Defects)

### Emoji variation selectors — known defect, acceptable v1

`string-width@^7` correctly returns 0 for most variation-selector code points in isolation, but certain ZWJ sequences used in multi-codepoint emoji (e.g., family group emoji, professions with skin tone modifiers) return an incorrect width of 2 even when rendered as a single 2-col glyph. The result is 0 extra columns rather than the expected 0, producing 2 extra padding characters.

This defect is **accepted as-is for v1** per Spec 287 § Edge Cases R5 (impact: Medium; probability: Low). The practical frequency in KOSMOS backend data is low because `data.go.kr` API responses do not systematically use multi-codepoint emoji in structured fields.

Tracking: no standalone issue at time of writing. If the defect affects more than 1% of rendered rows in soak testing (`bun test:soak`), open a dedicated issue and evaluate either a custom ZWJ-strip pre-pass or upgrading to a future `string-width` version that resolves the edge case.

---

## References

- [ink#688](https://github.com/vadimdemedes/ink/issues/688) — CJK characters miscounted as 1 column
- [ink#759](https://github.com/vadimdemedes/ink/issues/759) — ZWJ / emoji variation selectors cause width drift
- [`string-width` npm package](https://www.npmjs.com/package/string-width) — Unicode-aware string width (pinned to `^7` in `tui/package.json`)
- Spec 287 `plan.md` § Primary Dependencies — declares `string-width@^7`
- Spec 287 `spec.md` § Assumptions, Assumption #3 — "CJK character width is handled by `string-width`; known edge cases (ink#688, ink#759) are documented in `tui/docs/cjk-width-known-issues.md`."
- Spec 287 `spec.md` § Edge Cases, R5 — risk entry for CJK width calculation
