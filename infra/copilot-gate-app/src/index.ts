/**
 * KOSMOS Copilot Review Gate — Cloudflare Worker
 *
 * GitHub App webhook handler that bridges Copilot Code Review (which only
 * leaves PR comments) into a Check Run gate (pass/fail in the Checks tab).
 *
 * Strategy: "GraphQL Re-Review Request + Optimistic Fallback"
 *
 *   opened/reopened → in_progress check (wait for first Copilot review)
 *   synchronize     → in_progress check + request Copilot re-review via
 *                     GraphQL requestReviewsByLogin mutation (botLogins).
 *                     Falls back to optimistic pass if mutation fails.
 *   pull_request_review (from Copilot) → update check to real result
 *
 * The requestReviewsByLogin mutation with botLogins field (added 2026-01-22)
 * is the only reliable programmatic way to trigger Copilot re-review.
 * The Ruleset review_on_push setting has ~1/3 failure rate per community
 * reports. REST API requested_reviewers does not support bot accounts.
 */

interface Env {
  GITHUB_APP_ID: string;
  GITHUB_APP_PRIVATE_KEY: string;
  GITHUB_WEBHOOK_SECRET: string;
}

// --- Crypto helpers ---

async function verifySignature(
  secret: string,
  payload: string,
  signature: string
): Promise<boolean> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(payload));
  const expected =
    "sha256=" +
    Array.from(new Uint8Array(sig))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  return expected === signature;
}

// --- GitHub App JWT ---

function base64url(data: ArrayBuffer | Uint8Array): string {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function pemToArrayBuffer(pem: string): ArrayBuffer {
  const b64 = pem
    .replace(/-----BEGIN RSA PRIVATE KEY-----/, "")
    .replace(/-----END RSA PRIVATE KEY-----/, "")
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\s/g, "");
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

async function createJWT(appId: string, privateKeyPem: string): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT" };
  const payload = { iat: now - 60, exp: now + 600, iss: appId };

  const encoder = new TextEncoder();
  const headerB64 = base64url(encoder.encode(JSON.stringify(header)));
  const payloadB64 = base64url(encoder.encode(JSON.stringify(payload)));
  const message = `${headerB64}.${payloadB64}`;

  const keyData = pemToArrayBuffer(privateKeyPem);
  const key = await crypto.subtle.importKey(
    "pkcs8",
    keyData,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    encoder.encode(message)
  );

  return `${message}.${base64url(signature)}`;
}

// --- GitHub API helpers ---

async function getInstallationToken(
  appId: string,
  privateKey: string,
  installationId: number
): Promise<string> {
  const jwt = await createJWT(appId, privateKey);
  const res = await fetch(
    `https://api.github.com/app/installations/${installationId}/access_tokens`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${jwt}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "kosmos-copilot-gate/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
      },
    }
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Failed to get installation token: ${res.status} ${body}`);
  }
  const data = (await res.json()) as { token: string };
  return data.token;
}

async function githubApi(
  token: string,
  method: string,
  path: string,
  body?: object
): Promise<unknown> {
  const res = await fetch(`https://api.github.com${path}`, {
    method,
    headers: {
      Authorization: `token ${token}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "kosmos-copilot-gate/1.0",
      "X-GitHub-Api-Version": "2022-11-28",
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GitHub API ${method} ${path}: ${res.status} ${text}`);
  }
  return res.json();
}

async function githubGraphQL(
  token: string,
  query: string,
  variables: Record<string, unknown>
): Promise<unknown> {
  const res = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: {
      Authorization: `bearer ${token}`,
      "Content-Type": "application/json",
      "User-Agent": "kosmos-copilot-gate/1.0",
    },
    body: JSON.stringify({ query, variables }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GitHub GraphQL: ${res.status} ${text}`);
  }
  const data = (await res.json()) as { errors?: Array<{ message: string }>; data: unknown };
  if (data.errors && data.errors.length > 0) {
    throw new Error(`GitHub GraphQL errors: ${data.errors.map(e => e.message).join(", ")}`);
  }
  return data.data;
}

// --- Constants ---

const COPILOT_BOTS = ["copilot-pull-request-reviewer[bot]", "Copilot"];
const COPILOT_BOT_LOGIN = "copilot-pull-request-reviewer[bot]";
const CHECK_NAME = "Copilot Review Gate";

const REQUEST_REVIEW_MUTATION = `
  mutation($input: RequestReviewsByLoginInput!) {
    requestReviewsByLogin(input: $input) {
      pullRequest { id }
    }
  }
`;

// File extensions that Copilot will not review (docs, config, assets)
const SKIP_EXTENSIONS = new Set([
  ".md", ".txt", ".rst", ".adoc",
  ".yml", ".yaml", ".toml", ".ini", ".cfg",
  ".json", ".lock",
  ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
  ".license", ".gitignore", ".gitattributes",
  ".editorconfig",
]);

// --- Severity classification ---

const CRITICAL_PATTERNS = [
  /🔴/,
  /\bCRITICAL\b/i,
  /\bsecurity\s+vulnerabilit/i,
  /\bsql\s+injection/i,
  /\bremote\s+code\s+execution/i,
  /\bhardcoded\s+(secret|credential|password|key)/i,
  /\bdata\s+loss/i,
  /\brace\s+condition/i,
];

const IMPORTANT_PATTERNS = [
  /🟡/,
  /\bIMPORTANT\b/i,
];

const SUGGESTION_PATTERNS = [
  /🟢/,
  /\bSUGGESTION\b/i,
  /\bconsider\s+(using|adding|replacing)/i,
  /\bnitpick/i,
  /\bstyle:/i,
  /\bminor:/i,
];

type Severity = "critical" | "important" | "suggestion";

function classifyComment(body: string): Severity {
  const firstLine = body.split("\n")[0];
  if (CRITICAL_PATTERNS.some((p) => p.test(firstLine))) return "critical";
  if (SUGGESTION_PATTERNS.some((p) => p.test(firstLine))) return "suggestion";
  if (IMPORTANT_PATTERNS.some((p) => p.test(firstLine))) return "important";
  // Default: unclassified comments are treated as "important"
  return "important";
}

// --- Types ---

interface PullRequestEvent {
  action: string;
  installation: { id: number };
  repository: { owner: { login: string }; name: string };
  pull_request: {
    number: number;
    node_id: string;
    user: { login: string };
    head: { sha: string };
    labels: Array<{ name: string }>;
  };
}

interface ReviewEvent extends PullRequestEvent {
  review: {
    id: number;
    user: { login: string };
    state: string;
    commit_id: string;
  };
}

// --- Check Run helpers ---

async function createCheckRun(
  token: string,
  owner: string,
  repo: string,
  sha: string,
  status: "in_progress" | "completed",
  conclusion: string | undefined,
  title: string,
  summary: string
): Promise<void> {
  await githubApi(token, "POST", `/repos/${owner}/${repo}/check-runs`, {
    name: CHECK_NAME,
    head_sha: sha,
    status,
    ...(conclusion ? { conclusion } : {}),
    output: { title, summary },
  });
}

async function updateOrCreateCheckRun(
  token: string,
  owner: string,
  repo: string,
  sha: string,
  conclusion: string,
  title: string,
  summary: string
): Promise<void> {
  // Find any existing check run for this commit
  const checkRuns = (await githubApi(
    token,
    "GET",
    `/repos/${owner}/${repo}/commits/${sha}/check-runs?check_name=${encodeURIComponent(CHECK_NAME)}&filter=latest`
  )) as { check_runs: Array<{ id: number; status: string }> };

  const existing = checkRuns.check_runs[0];

  if (existing) {
    await githubApi(
      token,
      "PATCH",
      `/repos/${owner}/${repo}/check-runs/${existing.id}`,
      {
        status: "completed",
        conclusion,
        output: { title, summary },
      }
    );
  } else {
    await createCheckRun(token, owner, repo, sha, "completed", conclusion, title, summary);
  }
}

// --- Event handlers ---

async function handlePullRequest(event: PullRequestEvent, env: Env): Promise<Response> {
  const { action, installation, repository, pull_request } = event;

  if (!["opened", "reopened", "synchronize"].includes(action)) {
    return new Response("Ignored action: " + action, { status: 200 });
  }

  const token = await getInstallationToken(
    env.GITHUB_APP_ID,
    env.GITHUB_APP_PRIVATE_KEY,
    installation.id
  );

  const owner = repository.owner.login;
  const repo = repository.name;
  const sha = pull_request.head.sha;

  // Auto-pass for bypass label
  const labels = (pull_request.labels ?? []).map((l) => l.name);
  if (labels.includes("copilot-review-bypass")) {
    await createCheckRun(
      token, owner, repo, sha, "completed", "success",
      "Bypassed — copilot-review-bypass label present",
      "This PR has been manually exempted from Copilot review gate."
    );
    return new Response("Bypass label detected", { status: 200 });
  }

  // Auto-pass for bot PRs
  if (pull_request.user.login.endsWith("[bot]")) {
    await createCheckRun(
      token, owner, repo, sha, "completed", "success",
      `Skipped — bot PR (${pull_request.user.login})`,
      "Copilot review is not required for automated bot PRs."
    );
    return new Response("Auto-passed bot PR", { status: 200 });
  }

  // Auto-pass if PR contains only non-code files (docs, config, assets)
  try {
    const prFiles = (await githubApi(
      token, "GET",
      `/repos/${owner}/${repo}/pulls/${pull_request.number}/files?per_page=100`
    )) as Array<{ filename: string }>;

    const hasCode = prFiles.some((f) => {
      const ext = f.filename.includes(".") ? "." + f.filename.split(".").pop()!.toLowerCase() : "";
      return !SKIP_EXTENSIONS.has(ext);
    });

    if (!hasCode) {
      await createCheckRun(
        token, owner, repo, sha, "completed", "success",
        "Skipped — docs/config-only changes",
        `All ${prFiles.length} changed file${prFiles.length !== 1 ? "s" : ""} are documentation or configuration. Copilot review is not applicable.`
      );
      console.log(`[${action}] Auto-passed docs-only PR #${pull_request.number} (${sha.slice(0, 7)})`);
      return new Response(`${action}: docs-only auto-pass`, { status: 200 });
    }
  } catch (err) {
    console.error(`[${action}] Failed to check PR files: ${err}`);
  }

  if (action === "opened" || action === "reopened") {
    // First open — wait for Copilot's initial review
    await createCheckRun(
      token, owner, repo, sha, "in_progress", undefined,
      "Waiting for Copilot Code Review",
      "Copilot has not submitted a review yet. This check will pass when Copilot finds no issues."
    );
    return new Response("Created pending check run", { status: 200 });
  }

  // synchronize — new commits pushed
  // Check if PR only contains non-code files (docs, config, assets)
  // Copilot does not review these, so auto-pass to prevent infinite pending
  try {
    const files = (await githubApi(
      token, "GET",
      `/repos/${owner}/${repo}/pulls/${pull_request.number}/files?per_page=100`
    )) as Array<{ filename: string }>;

    const hasCodeFiles = files.some((f) => {
      const ext = f.filename.includes(".") ? "." + f.filename.split(".").pop()!.toLowerCase() : "";
      return !SKIP_EXTENSIONS.has(ext);
    });

    if (!hasCodeFiles) {
      await createCheckRun(
        token, owner, repo, sha, "completed", "success",
        "Skipped — docs/config-only changes",
        `All ${files.length} changed file${files.length !== 1 ? "s" : ""} are documentation or configuration. Copilot review is not applicable.`
      );
      console.log(`[sync] Auto-passed docs-only PR #${pull_request.number} (${sha.slice(0, 7)})`);
      return new Response("Synchronize: docs-only auto-pass", { status: 200 });
    }
  } catch (err) {
    console.error(`[sync] Failed to check PR files: ${err}`);
    // Continue with normal flow if file check fails
  }

  // Create in_progress check and request Copilot re-review via GraphQL mutation.
  // The requestReviewsByLogin mutation with botLogins field (added 2026-01-22)
  // is the only reliable way to trigger Copilot re-review programmatically.
  await createCheckRun(
    token, owner, repo, sha, "in_progress", undefined,
    "Waiting for Copilot Code Review",
    "New commits pushed. Copilot re-review has been requested. This check will update when Copilot completes its review."
  );

  // Request Copilot re-review via GraphQL
  try {
    await githubGraphQL(token, REQUEST_REVIEW_MUTATION, {
      input: {
        pullRequestId: pull_request.node_id,
        botLogins: [COPILOT_BOT_LOGIN],
        union: true,
      },
    });
    console.log(`[sync] Requested Copilot re-review for PR #${pull_request.number} (${sha.slice(0, 7)})`);
  } catch (err) {
    // If re-review request fails, fall back to optimistic pass so the check never hangs
    console.error(`[sync] Failed to request Copilot re-review: ${err}`);
    await createCheckRun(
      token, owner, repo, sha, "completed", "success",
      "Passed — Copilot re-review request failed",
      [
        "New commits pushed. Could not request Copilot re-review (GraphQL error).",
        "Check passed optimistically. If Copilot reviews later, this will be updated.",
      ].join("\n")
    );
  }

  return new Response("Synchronize: requested Copilot re-review", { status: 200 });
}

async function handleReview(event: ReviewEvent, env: Env): Promise<Response> {
  const { review, installation, repository, pull_request } = event;

  // Only process Copilot reviews
  if (!COPILOT_BOTS.includes(review.user.login)) {
    return new Response("Not a Copilot review: " + review.user.login, { status: 200 });
  }

  console.log(`[review] from="${review.user.login}" state="${review.state}" commit="${review.commit_id}"`);

  const token = await getInstallationToken(
    env.GITHUB_APP_ID,
    env.GITHUB_APP_PRIVATE_KEY,
    installation.id
  );

  const owner = repository.owner.login;
  const repo = repository.name;
  const sha = pull_request.head.sha;
  const prNumber = pull_request.number;
  const reviewId = review.id;

  // Fetch inline comments for this review (top-level only, skip replies)
  const allComments = (await githubApi(
    token,
    "GET",
    `/repos/${owner}/${repo}/pulls/${prNumber}/reviews/${reviewId}/comments`
  )) as Array<{ path: string; line: number | null; body: string; in_reply_to_id: number | null }>;

  const comments = allComments.filter((c) => c.in_reply_to_id === null);
  const count = comments.length;

  // Classify by severity
  const classified = comments.map((c) => ({ ...c, severity: classifyComment(c.body) }));
  const critical = classified.filter((c) => c.severity === "critical");
  const important = classified.filter((c) => c.severity === "important");
  const suggestions = classified.filter((c) => c.severity === "suggestion");

  let conclusion: string;
  let title: string;
  let summary: string;

  if (count === 0) {
    conclusion = "success";
    title = "Copilot review passed — no issues found";
    summary = "Copilot Code Review completed with no inline comments.";
  } else if (critical.length > 0) {
    conclusion = "failure";
    title = `Copilot found ${critical.length} critical issue${critical.length > 1 ? "s" : ""}`;
    const issues = critical
      .map((c) => `- \`${c.path}${c.line ? ":" + c.line : ""}\` — ${c.body.split("\n")[0].slice(0, 120)}`)
      .join("\n");
    summary = [
      `Copilot Code Review found ${critical.length} critical issue${critical.length > 1 ? "s" : ""}, ${important.length} important, ${suggestions.length} suggestion${suggestions.length !== 1 ? "s" : ""}.`,
      "Address the critical issues and push fixes to trigger a re-review.",
      "",
      "**Critical Issues:**",
      issues,
    ].join("\n");
  } else if (important.length >= 3) {
    conclusion = "failure";
    title = `Copilot found ${important.length} important issues (threshold: 3+)`;
    const issues = important
      .map((c) => `- \`${c.path}${c.line ? ":" + c.line : ""}\` — ${c.body.split("\n")[0].slice(0, 120)}`)
      .join("\n");
    summary = [
      `Copilot Code Review found ${important.length} important issue${important.length > 1 ? "s" : ""} and ${suggestions.length} suggestion${suggestions.length !== 1 ? "s" : ""} (no critical).`,
      "Too many important issues (threshold: 3+). Address them and push fixes.",
      "",
      "**Important Issues:**",
      issues,
    ].join("\n");
  } else {
    conclusion = "success";
    title = `Copilot review passed (${important.length} important, ${suggestions.length} suggestion${suggestions.length !== 1 ? "s" : ""})`;
    const noted = [...important, ...suggestions];
    const issues = noted.length > 0
      ? noted.map((c) => `- \`${c.path}${c.line ? ":" + c.line : ""}\` — ${c.body.split("\n")[0].slice(0, 120)}`).join("\n")
      : "";
    summary = [
      `Copilot Code Review completed. ${important.length} important, ${suggestions.length} suggestion${suggestions.length !== 1 ? "s" : ""} (no critical).`,
      "Below threshold — check passed. Review the comments for optional improvements.",
      ...(issues ? ["", "**Notes:**", issues] : []),
    ].join("\n");
  }

  // Update or create check run — this overwrites any optimistic pass
  await updateOrCreateCheckRun(token, owner, repo, sha, conclusion, title, summary);

  console.log(`[review] PR #${prNumber} → ${conclusion} (${critical.length} critical, ${important.length} important, ${suggestions.length} suggestions)`);
  return new Response(`Check run → ${conclusion}`, { status: 200 });
}

// --- Worker entry point ---

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "POST") {
      return new Response("KOSMOS Copilot Gate is running.", { status: 200 });
    }

    const signature = request.headers.get("x-hub-signature-256");
    if (!signature) {
      return new Response("Missing signature", { status: 401 });
    }

    const body = await request.text();
    const valid = await verifySignature(env.GITHUB_WEBHOOK_SECRET, body, signature);
    if (!valid) {
      return new Response("Invalid signature", { status: 401 });
    }

    const event = request.headers.get("x-github-event");
    const payload = JSON.parse(body);

    try {
      switch (event) {
        case "pull_request":
          return await handlePullRequest(payload as PullRequestEvent, env);
        case "pull_request_review":
          return await handleReview(payload as ReviewEvent, env);
        default:
          return new Response("Ignored event: " + event, { status: 200 });
      }
    } catch (err) {
      console.error("Handler error:", err);
      return new Response("Internal error: " + String(err), { status: 500 });
    }
  },
};
