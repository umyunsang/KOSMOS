/**
 * KOSMOS Copilot Review Gate — Cloudflare Worker
 *
 * Receives GitHub webhook events and manages the "Copilot Review Gate"
 * check run. Unlike GitHub Actions, a GitHub App webhook handler is not
 * subject to the "untrusted bot actor" restriction, so it can react to
 * Copilot's pull_request_review events in real time.
 *
 * Flow:
 *   pull_request (opened/synchronize) → create in_progress check run
 *   pull_request_review (from Copilot) → count inline comments → pass/fail
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

// --- Event handlers ---

const COPILOT_BOTS = ["copilot-pull-request-reviewer[bot]", "Copilot"];
const CHECK_NAME = "Copilot Review Gate";

interface PullRequestEvent {
  action: string;
  installation: { id: number };
  repository: { owner: { login: string }; name: string };
  pull_request: {
    number: number;
    user: { login: string };
    head: { sha: string };
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

async function handlePullRequest(event: PullRequestEvent, env: Env): Promise<Response> {
  const { action, installation, repository, pull_request } = event;

  // Only handle opened, reopened, synchronize
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

  // Auto-pass for bot PRs — no Copilot review needed
  if (pull_request.user.login.endsWith("[bot]")) {
    await githubApi(token, "POST", `/repos/${owner}/${repo}/check-runs`, {
      name: CHECK_NAME,
      head_sha: sha,
      status: "completed",
      conclusion: "success",
      output: {
        title: `Skipped — bot PR (${pull_request.user.login})`,
        summary: "Copilot review is not required for automated bot PRs.",
      },
    });
    return new Response("Auto-passed bot PR: " + pull_request.user.login, { status: 200 });
  }

  // Create in_progress check run (pending in UI)
  await githubApi(token, "POST", `/repos/${owner}/${repo}/check-runs`, {
    name: CHECK_NAME,
    head_sha: sha,
    status: "in_progress",
    output: {
      title: "Waiting for Copilot Code Review",
      summary:
        "Copilot has not submitted a review yet. This check will pass when Copilot finds no issues.",
    },
  });

  return new Response("Created pending check run", { status: 200 });
}

async function handleReview(event: ReviewEvent, env: Env): Promise<Response> {
  const { review, installation, repository, pull_request } = event;

  console.log(`[review] user.login="${review.user.login}" state="${review.state}" commit="${review.commit_id}"`);

  // Only process Copilot reviews
  if (!COPILOT_BOTS.includes(review.user.login)) {
    console.log(`[review] Skipped: expected one of ${COPILOT_BOTS} got "${review.user.login}"`);
    return new Response("Not a Copilot review: " + review.user.login, { status: 200 });
  }

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

  // Fetch inline comments for this specific review
  const comments = (await githubApi(
    token,
    "GET",
    `/repos/${owner}/${repo}/pulls/${prNumber}/reviews/${reviewId}/comments`
  )) as Array<{ path: string; line: number | null; body: string }>;

  const count = comments.length;
  let conclusion: string;
  let title: string;
  let summary: string;

  if (count === 0) {
    conclusion = "success";
    title = "Copilot review passed — no issues found";
    summary = "Copilot Code Review completed with no inline comments.";
  } else {
    conclusion = "failure";
    title = `Copilot found ${count} issue${count > 1 ? "s" : ""}`;
    const issues = comments
      .map(
        (c) =>
          `- \`${c.path}${c.line ? ":" + c.line : ""}\` — ${c.body.split("\n")[0].slice(0, 120)}`
      )
      .join("\n");
    summary = [
      `Copilot Code Review left ${count} inline comment${count > 1 ? "s" : ""}.`,
      "Address the comments and push fixes to trigger a re-review.",
      "",
      "**Issues:**",
      issues,
    ].join("\n");
  }

  // Find existing in_progress check run or create new one
  const checkRuns = (await githubApi(
    token,
    "GET",
    `/repos/${owner}/${repo}/commits/${sha}/check-runs?check_name=${encodeURIComponent(CHECK_NAME)}&filter=latest`
  )) as { check_runs: Array<{ id: number; status: string }> };

  const pending = checkRuns.check_runs.find((cr) => cr.status !== "completed");

  if (pending) {
    await githubApi(
      token,
      "PATCH",
      `/repos/${owner}/${repo}/check-runs/${pending.id}`,
      {
        status: "completed",
        conclusion,
        output: { title, summary },
      }
    );
  } else {
    await githubApi(token, "POST", `/repos/${owner}/${repo}/check-runs`, {
      name: CHECK_NAME,
      head_sha: sha,
      status: "completed",
      conclusion,
      output: { title, summary },
    });
  }

  return new Response(`Check run → ${conclusion}`, { status: 200 });
}

// --- Worker entry point ---

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "POST") {
      return new Response("KOSMOS Copilot Gate is running.", { status: 200 });
    }

    // Verify webhook signature
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
