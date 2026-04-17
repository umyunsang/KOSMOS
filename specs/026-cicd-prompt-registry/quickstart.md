# Quickstart: CI/CD & Prompt Registry (Spec 026)

**Audience**: New KOSMOS contributor who wants to (a) get a working dev environment in one minute, (b) edit a prompt and see the shadow-eval workflow run against their change, (c) dry-run the release manifest locally before pushing a tag.

**Prerequisites**: Docker Desktop (or Colima / Podman), VS Code with the "Dev Containers" extension, a Git checkout of `umyunsang/KOSMOS`, and a GitHub account with read access to the repo.

## A. First-time contributor — one-shot devcontainer onboarding

```bash
# From a shell on your host machine:
git clone https://github.com/umyunsang/KOSMOS.git
cd KOSMOS
code .
```

In VS Code: open the Command Palette (⇧⌘P) → `Dev Containers: Reopen in Container`.

What happens next:

1. VS Code reads `.devcontainer/devcontainer.json`.
2. It pulls `mcr.microsoft.com/devcontainers/python:3.12` and layers the uv feature on top.
3. The `postCreateCommand` runs `uv sync`, creating `.venv/` inside the container with every dependency resolved from `uv.lock`.
4. The container opens a terminal inside `/workspaces/KOSMOS`.

**Smoke test** — inside the devcontainer terminal:

```bash
uv run pytest -q
```

If this command completes green, your environment matches the CI matrix. No further host-side setup is needed.

**Port forwards** (already wired in `devcontainer.json` — you don't need to do anything):

- `4000` — LiteLLM proxy (when you run it locally via `docker compose up litellm-proxy`)
- `4318` — OTEL collector OTLP/HTTP ingress (when observability stack is running)

## B. Edit a prompt and observe shadow-eval

Prompts live under `prompts/` at repo root. v1 files:

- `prompts/system_v1.md` — platform identity + language + tool-use + personal-data reminder
- `prompts/session_guidance_v1.md` — geocoding-first rule + no-memory-fill rule + worked example
- `prompts/compact_v1.md` — session_compact summary header + section scaffolding

### B.1 Edit workflow

```bash
# 1. Make the change.
vim prompts/system_v1.md

# 2. Regenerate prompts/manifest.yaml so the sha256 field matches.
uv run python -m kosmos.context.prompt_loader --regenerate-manifest

# 3. Commit on a feature branch.
git checkout -b feat/prompt-tweak-example
git add prompts/manifest.yaml prompts/system_v1.md
git commit -m "feat(prompts): tweak system prompt wording"
git push -u origin feat/prompt-tweak-example
```

### B.2 Open a PR — what CI does automatically

1. **shadow-eval workflow triggers** because your PR modified a file under `prompts/**`.
2. The workflow checks out both your PR head and the merge-base with `main`.
3. It runs the fixture-only battery at `tests/shadow_eval/battery.py` twice:
   - once against the merge-base prompts → spans tagged `deployment.environment=main`
   - once against your PR-head prompts → spans tagged `deployment.environment=shadow`
4. Both runs produce a JSON artifact attached to the workflow run (visible from the PR's "Checks" tab).
5. The battery is restricted to mock transports — no outbound call to `*.data.go.kr` is possible. Any attempt to make a live API call fails the job.

**Timeout**: 15 minutes (configured in `.github/workflows/shadow-eval.yml`). Timeout failures don't block the main lint/test jobs on the PR — they surface only as a red check on the `shadow-eval` lane.

### B.3 Inspect the shadow-eval artifact locally

```bash
# Download the workflow artifact via gh CLI.
gh run download --name shadow-eval-report --dir ./shadow-eval-out

# Inspect the two span batches.
jq '.spans | group_by(.attributes."deployment.environment") | map({env: .[0].attributes."deployment.environment", count: length})' \
   shadow-eval-out/eval-report.json
```

Expected output:

```json
[
  { "env": "main",   "count": 42 },
  { "env": "shadow", "count": 42 }
]
```

Both runs see the same battery input ids; only the prompt bytes differ.

## C. Local Docker build + release-manifest dry run

### C.1 Build the runtime image locally

```bash
# From repo root on your host (not inside the devcontainer).
docker build -f docker/Dockerfile -t kosmos:local .
```

Check the constraints that CI will also check (SC-001):

```bash
# 1. Image size must be <= 2 GB.
docker inspect --format='{{.Size}}' kosmos:local | awk '{ printf "%.2f GB\n", $1/1024/1024/1024 }'

# 2. Runtime user must be UID 1000 (non-root).
docker run --rm kosmos:local id -u    # expected: 1000
```

Both checks run automatically in the `docker-build` job on every push to `main` and on PRs that modify `docker/**`, `pyproject.toml`, or `uv.lock`.

### C.2 Dry-run the release manifest

```bash
# Simulate what .github/workflows/release-manifest.yml would emit at tag time.
COMMIT_SHA=$(git rev-parse HEAD)
UV_LOCK_HASH="sha256:$(sha256sum uv.lock | awk '{ print $1 }')"

# Ask the Prompt Registry for the sha256 of every registered prompt.
uv run python -m kosmos.context.prompt_loader --emit-hashes > /tmp/prompt-hashes.json

# Render a candidate manifest.
uv run python -m tools.release_manifest.render \
    --commit-sha "$COMMIT_SHA" \
    --uv-lock-hash "$UV_LOCK_HASH" \
    --docker-digest "sha256:$(docker inspect --format='{{index .RepoDigests 0}}' kosmos:local | awk -F@ '{print $2}' | sed 's/^sha256://')" \
    --prompt-hashes-file /tmp/prompt-hashes.json \
    --friendli-model-id "$KOSMOS_FRIENDLI_MODEL_ID" \
    --litellm-proxy-version unknown \
    --out /tmp/release-manifest.yaml

# Validate against the JSON Schema.
uv run python -m jsonschema -i /tmp/release-manifest.yaml \
    specs/026-cicd-prompt-registry/contracts/release-manifest.schema.json
```

A successful validation means the real workflow will produce a file that passes the same check. No tag has been pushed; nothing is committed; this is purely a local dry run.

## D. Toggling the optional Langfuse Prompt Management integration

By default the Prompt Registry is **repository-only** — no outbound network call at startup. To opt into Langfuse:

```bash
# Set the flag and credentials in your local .env (never commit .env).
export KOSMOS_PROMPT_REGISTRY_LANGFUSE=true
export KOSMOS_LANGFUSE_HOST="https://cloud.langfuse.com"
export KOSMOS_LANGFUSE_PUBLIC_KEY="pk-lf-..."
export KOSMOS_LANGFUSE_SECRET_KEY="sk-lf-..."

# Install the optional extras (only needed once per venv).
uv sync --extra langfuse

# Run the platform normally. PromptLoader now consults Langfuse AS WELL AS the repo;
# if the hashes disagree, startup fails (fail-closed).
uv run python -m kosmos.cli repl
```

When the flag is unset, no `langfuse` import even happens — the extras dependency is strictly opt-in (AGENTS.md hard rule: no new top-level runtime dependency).

## E. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `PromptRegistryError: hash mismatch for system_v1` at startup | You edited `prompts/system_v1.md` but forgot to regenerate `manifest.yaml`. | `uv run python -m kosmos.context.prompt_loader --regenerate-manifest` |
| `PromptRegistryError: orphan prompt file prompts/foo_v1.md` | You added a `.md` file under `prompts/` without adding a manifest entry. | Either add the entry to `manifest.yaml` or remove the file. |
| `shadow-eval` job skipped on your PR | Your PR doesn't touch `prompts/**`. | Intentional — the job is path-filtered. If you actually want it to run, modify a `prompts/*.md` file. |
| `docker-build` job fails with "image size 2.4 GB exceeds 2 GB budget" | A large dev dependency crept into the runtime stage. | Check the `COPY --from=builder /app/.venv /app/.venv` line — only the resolved venv should cross the stage boundary, not `/root/.cache/uv`. |
| Manifest job fails with "uv.lock drift detected" | You edited `pyproject.toml` without running `uv lock`. | `uv lock && git add uv.lock && git commit -m "chore: refresh uv.lock"` |

## F. What NOT to do

- ❌ **Do not edit `docs/release-manifests/*.yaml` by hand.** These files are append-only and machine-authored. Manual edits will be rejected at review.
- ❌ **Do not add `requirements.txt`, `setup.py`, or `Pipfile`.** AGENTS.md hard rule — `uv` + `pyproject.toml` only.
- ❌ **Do not call live `data.go.kr` APIs from CI or from the shadow-eval battery.** Fixtures only. The CI enforces this with `httpx.MockTransport`.
- ❌ **Do not commit `.env`, Langfuse keys, FriendliAI keys, or `GHCR_TOKEN` values** to the repository. CI reads these from GitHub Actions secrets / OIDC.

## G. Where to read next

- `specs/026-cicd-prompt-registry/spec.md` — the normative feature spec with FR-A01..F05, NFR-01..07, SC-001..007.
- `specs/026-cicd-prompt-registry/data-model.md` — Pydantic v2 models for `PromptManifestEntry`, `PromptManifest`, `ReleaseManifest`.
- `specs/026-cicd-prompt-registry/research.md` — the five external references and four internal references that grounded this design.
- `docs/vision.md § Reference materials` — the canonical reference table for every architectural decision in KOSMOS.
- `AGENTS.md` — the hard rules every contributor and every AI agent MUST follow.
