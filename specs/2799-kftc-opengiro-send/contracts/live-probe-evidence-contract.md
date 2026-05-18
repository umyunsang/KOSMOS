# Contract: Future Live Probe Evidence

Live KFTC OpenGiro execution is not complete in this epic. A future live-validation task must capture sanitized direct-curl evidence before flipping any adapter from mock to live.

## Required Evidence Per Endpoint

| Evidence | Requirement |
|---|---|
| Official endpoint URL | Must match KFTC public or approved gated documentation |
| HTTP method | Must match KFTC documentation |
| Request headers | Authorization/token values redacted |
| Request body/query | Personal identifiers and financial account data redacted |
| Response headers | Stored with sensitive values redacted |
| Response body | Stored with tokens, payment URLs, and personal identifiers redacted or fixture-replaced |
| Result classification | Map to `pending`, `succeeded`, `failed`, or `rejected` with rationale |

## Default CI Rule

Live probe artifacts are evidence only. CI tests must use fixtures and must not call KFTC.

