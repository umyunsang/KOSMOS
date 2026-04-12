# KOSMOS Copilot Review Gate — Setup Guide

## Overview

A Cloudflare Worker + GitHub App that gates PR merges on Copilot Code Review results.
Unlike GitHub Actions, a GitHub App webhook is not blocked by the "untrusted bot actor"
restriction, so it reacts to Copilot reviews in real time without polling.

## Prerequisites

- Cloudflare account (free tier is sufficient)
- GitHub repository admin access
- Node.js 18+ and npm

## Step 1: Deploy Cloudflare Worker

```bash
cd infra/copilot-gate-app
npm install
npx wrangler login          # Opens browser for Cloudflare auth
npx wrangler deploy          # Deploys worker, prints URL
```

Note the deployed URL (e.g., `https://kosmos-copilot-gate.<your-subdomain>.workers.dev`).
You will need this for the GitHub App webhook URL.

## Step 2: Create GitHub App

Go to: **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**

Fill in these fields:

| Field | Value |
|-------|-------|
| **GitHub App name** | `KOSMOS Copilot Gate` (or any unique name) |
| **Homepage URL** | `https://github.com/kosmos-kr/KOSMOS` |
| **Webhook URL** | `https://kosmos-copilot-gate.<your-subdomain>.workers.dev` |
| **Webhook secret** | Generate one: `openssl rand -hex 32` |
| **Permissions** | |
| → Checks | Read & Write |
| → Pull requests | Read-only |
| **Subscribe to events** | |
| → Pull request | ✅ |
| → Pull request review | ✅ |
| **Where can this GitHub App be installed?** | Only on this account |

Click **Create GitHub App**.

## Step 3: Generate Private Key

On the App settings page, scroll to **Private keys** → **Generate a private key**.
A `.pem` file will download. Keep it safe.

## Step 4: Install App on Repository

On the App settings page → **Install App** (left sidebar) → Select `kosmos-kr/KOSMOS` → Install.

## Step 5: Configure Worker Secrets

```bash
cd infra/copilot-gate-app

# App ID (shown on the App settings page, numeric)
npx wrangler secret put GITHUB_APP_ID
# Paste the App ID number, then Ctrl+D

# Private key
npx wrangler secret put GITHUB_APP_PRIVATE_KEY
# Paste the full PEM content (including BEGIN/END lines), then Ctrl+D

# Webhook secret (same value from Step 2)
npx wrangler secret put GITHUB_WEBHOOK_SECRET
# Paste the secret, then Ctrl+D
```

## Step 6: Remove Old Polling Workflow

Delete `.github/workflows/copilot-gate.yml` from the repository (it's no longer needed).

## Step 7: Verify

1. Create a test PR or push to an existing PR
2. Check the **Checks** tab — "Copilot Review Gate" should appear as `in_progress`
3. Wait for Copilot to review
4. Check should update to `success` (no issues) or `failure` (issues found)

## Troubleshooting

### Check Worker Logs
```bash
npx wrangler tail
```

### Verify Webhook Delivery
GitHub → Settings → Developer settings → GitHub Apps → your app → Advanced → Recent Deliveries

### Common Issues

- **401 Invalid signature**: Webhook secret mismatch between GitHub App and Worker secret
- **Failed to get installation token**: App ID or private key incorrect
- **Check run not appearing**: App not installed on the repo, or missing `checks:write` permission
