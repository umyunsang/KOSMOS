# Quickstart — New Contributor Onboarding (post-#468)

**Target audience**: a developer who just cloned `umyunsang/KOSMOS` for the first time.
**Goal**: reach green `uv run pytest` inside 10 minutes (SC-007).
**Reference**: Epic #468 · `docs/configuration.md` · `spec.md §User Story 2`.

---

## 0. Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) package manager
- macOS or Linux (Windows via WSL2)

```bash
python3 --version       # expect 3.12+
uv --version            # expect 0.4+
```

## 1. Clone + install

```bash
git clone git@github.com:umyunsang/KOSMOS.git
cd KOSMOS
uv sync
```

## 2. Create `.env` from template

```bash
cp .env.example .env
```

> **Warning**: `.env` is a symlink-safe local file — `git` ignores it. Never `git add` it. Never edit `.env.example` to contain a real value.

## 3. Fill in required secrets

Open `.env` and replace each `<redacted>` with your credential. **Mandatory** in all environments:

| Variable | How to obtain |
|----------|---------------|
| `KOSMOS_FRIENDLI_TOKEN` | [FriendliAI Suite](https://suite.friendli.ai/) → Personal Settings → Tokens |
| `KOSMOS_KAKAO_API_KEY` | [Kakao Developers](https://developers.kakao.com) → Apps → REST API key |
| `KOSMOS_DATA_GO_KR_API_KEY` | [data.go.kr](https://www.data.go.kr/) → 마이페이지 → 인증키 |

**Optional** (only if you plan to exercise those surfaces):

| Variable | Used by |
|----------|---------|
| `KOSMOS_JUSO_CONFM_KEY` | 행정안전부 도로명주소 (JUSO tool) |
| `KOSMOS_SGIS_KEY` / `KOSMOS_SGIS_SECRET` | SGIS 통계지리정보 |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Langfuse trace export (#501) |

**Complete registry**: `docs/configuration.md` (the canonical `KOSMOS_*` reference table).

## 4. Verify startup guard

Run the CLI once to confirm the guard is satisfied:

```bash
uv run kosmos --help
```

**Expected (all required vars set)**: the CLI `--help` text prints immediately (<100 ms guard budget).

**If a required var is missing**, you'll see exactly one line on stderr:

```
KOSMOS config error [env=dev]: missing required variables: KOSMOS_KAKAO_API_KEY. See https://github.com/umyunsang/KOSMOS/blob/main/docs/configuration.md
```

→ edit `.env`, re-run. That single line is the complete remediation path.

## 5. Run the test suite

```bash
uv run pytest
```

**Expected**: all tests pass. Live-API tests are marked `@pytest.mark.live` and skipped by default; enable with `uv run pytest -m live` only when you have real credentials and agree to the per-call costs.

## 6. Run the audit scripts locally (optional, CI-enforced)

```bash
./scripts/audit-secrets.sh              # workflow secret hygiene
uv run python scripts/audit-env-registry.py | jq .verdict
```

Both should exit `0` / print `"clean"`. CI runs them as pre-test gates; running locally gives you the same signal pre-push.

## 7. Environment activation flag (optional)

By default `KOSMOS_ENV=dev`. Set to `prod` only when running against production APIs with full credentials:

```bash
KOSMOS_ENV=prod uv run kosmos
```

In `prod` mode the guard demands *all* conditional-required variables (e.g., `LANGFUSE_*`) — missing any of them fails fast with the same single-line error.

## 8. Rollback

Broke something? The entire Epic #468 surface is contained:

```bash
git revert <merge-commit-sha>    # restore prior config state
cp .env.backup .env              # if you kept a backup
```

No data-store changes occurred — configuration is code + env vars only. SC-008 guarantees rollback to a known-good state in under 15 minutes.

---

## Troubleshooting

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `KOSMOS config error [env=dev]: missing required variables: ...` | `.env` missing or incomplete | edit `.env`; re-run |
| `pytest` fails with "live API quota exceeded" | you ran `-m live` without credits | drop `-m live` (default skip) |
| `audit-secrets.sh: FORBIDDEN pattern` | you added a `${{ secrets.X_TOKEN }}` to `ci.yml` | move to Infisical + OIDC per `contracts/ci-workflow.md` |
| `audit-env-registry.py: in_code_not_in_registry` | you added a `KOSMOS_*` var without a registry row | add row to `docs/configuration.md` |
| Guard exits 78 but all vars look set | values are whitespace-only; the guard treats them as missing | re-check `.env` for `KOSMOS_X= ` (trailing space) |

## Where to ask

- **Usage questions**: GitHub Discussions.
- **Security concerns**: email `umyunsang` (listed in `LICENSE`).
- **Spec / architecture**: reference `docs/vision.md` first, then open an Issue with the `initiative` or `epic` label.
