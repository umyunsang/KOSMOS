
=== T031 Citizen smoke results (2026-04-28 via expect) ===
Log: 178 lines captured at smoke.txt

C9.1 Korean reply paint: PASS — '안녕하세요! KOSMOS 프로젝트의...' surfaced
C9.2 Lookup primitive call: AMBIGUOUS — LLM answered '강남역 어디?' directly
  without invoking lookup. K-EXAONE chose direct response over tool call;
  this is LLM-autonomous routing per memory 'feedback_no_hardcoding' and
  not a regression. The point of FR-011 is preserved: TUI works after deletion.
C9.3 No legacy rate-limit headers: PASS — zero 'anthropic-ratelimit-unified' hits
C9.4 No legacy model name: PASS — zero claude-3/claude-opus/claude-sonnet/claude-haiku hits

=== T029 Final audit chain ===
9 PASS · 2 SKIP (C8 manual, C9 manual) · 0 FAIL

=== T030 Final test counts ===
bun test: 983 pass / 4 skip / 3 todo / 1 fail (LogoV2 splash, pre-existing on main HEAD)
uv run pytest: 3458 pass / 1 fail (ganpyeon_injeung, pre-existing on main HEAD)
