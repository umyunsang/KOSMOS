# Copilot Review Gate — Operations Guide

Detailed operational procedures for the Copilot Review Gate. See `AGENTS.md` for the summary and `docs/conventions.md § Copilot Review Gate` for pass/fail criteria.

## Architecture

Cloudflare Worker GitHub App (`infra/copilot-gate-app/`) that bridges Copilot Code Review comments into a Check Run (pass/fail in the Checks tab).

**Flow:**
1. PR opened/reopened → `in_progress` check, waits for Copilot's first review
2. New commits pushed (`synchronize`) → `in_progress` check + GraphQL `requestReviewsByLogin` triggers Copilot re-review
3. Copilot review arrives → classify comments by severity → update check run

**Auto-pass conditions** (no Copilot review needed):
- PR has `copilot-review-bypass` label
- PR author is a bot (`[bot]` suffix)
- PR contains only non-code files (docs, config, assets)

## Re-review failure procedure

The GraphQL `requestReviewsByLogin` mutation has a **~1/3 failure rate**. After every push to a PR branch:

### Step 1: Check gate status

Wait 2 minutes after push. If the gate stays `in_progress` without Copilot starting:

```bash
gh pr checks <PR_NUMBER> --json name,status,conclusion \
  --jq '.[] | select(.name == "Copilot Review Gate")'
```

### Step 2: Manually request re-review

```bash
# Get PR node ID
PR_NODE_ID=$(gh api repos/umyunsang/KOSMOS/pulls/<PR_NUMBER> --jq '.node_id')

# Request Copilot re-review via GraphQL
gh api graphql -f query='
  mutation($input: RequestReviewsByLoginInput!) {
    requestReviewsByLogin(input: $input) {
      pullRequest { id }
    }
  }
' -F input[pullRequestId]="$PR_NODE_ID" \
  -F input[botLogins][]=copilot-pull-request-reviewer[bot] \
  -F input[union]:=true
```

### Step 3: If re-review still fails

If Copilot does not start reviewing within 2 more minutes after manual request:

```bash
gh pr edit <PR_NUMBER> --add-label copilot-review-bypass
```

This causes the gate to auto-pass on the next webhook event.

## Deployment

```bash
cd infra/copilot-gate-app && npx wrangler deploy
```

Deploy after any change to `infra/copilot-gate-app/src/index.ts`. The Worker is not auto-deployed on git push.

## Fail-closed safety

The Worker implements fail-closed behavior for API eventual consistency:
- If Copilot's review body says "generated N comments" but the API returns 0 after retries, the gate **fails** (not passes)
- Comments are fetched with pagination (`fetchAllPages`) and retried up to 3 times with increasing delays
- Retries only trigger when `expectedCount > 0` (known positive count from review body)
