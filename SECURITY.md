# Security Policy

## Supported Versions

KOSMOS is in early development and has no stable releases yet. Security fixes are applied to the `main` branch only.

| Version | Supported |
|---|---|
| `main` | Yes |
| Other | No |

## Reporting a Vulnerability

**Please do not report security issues in public GitHub issues.**

If you discover a vulnerability — particularly one involving citizen data exposure, authentication bypass, permission pipeline circumvention, or prompt-injection that leaks sensitive API responses — report it privately through one of the following channels:

1. **GitHub Private Vulnerability Reporting** (preferred)
   Navigate to the repository's **Security** tab and click **Report a vulnerability**.

2. **Direct contact**
   Open a minimal public issue titled `security: contact request` without details, and the maintainer will reach out to establish a private channel.

## What to include

A useful report contains:

- A clear description of the issue and its impact
- Steps to reproduce, including minimal inputs
- The affected component (query engine, tool adapter, permission pipeline, etc.)
- Any suggested mitigation, if you have one

## Response expectations

This is a student-led research project. The maintainer will:

- Acknowledge the report within **7 days**
- Provide an initial assessment within **14 days**
- Target a fix or mitigation within **30 days** for high-severity issues

Timelines may extend for complex issues or during exam periods. The reporter will be kept informed.

## Disclosure

Coordinated disclosure is preferred. Once a fix is merged, the reporter will be credited in the release notes unless they request anonymity.

## Out of scope

- Vulnerabilities in upstream dependencies (report to the upstream project)
- Issues in `data.go.kr` APIs themselves (report to the operating ministry)
- Model-level issues in K-EXAONE (report to LG AI Research)
- Theoretical issues without a reproducible impact on KOSMOS
