# Mock: npki_crypto

**Mirror axis**: shape
**Source reference**: PyPinkSign (https://github.com/bandoche/PyPinkSign) — MIT License; PKCS#7 (RFC 2315 / RFC 5652 CMS), PKCS#12 (RFC 7292)
**License**: MIT (PyPinkSign); referenced RFCs are public standards
**Scope**: Reproduces the **cryptographic layer only** of Korean NPKI (공인인증서) operations — specifically PKCS#7 detached signature creation/verification and PKCS#12 certificate bundle load/parse using public RFC-defined formats; does NOT include the NPKI portal session, certificate issuance workflow, or any interaction with the YESSIGN / KOSCOM / NHN certificate authorities.

> **IMPORTANT**: The NPKI portal session (certificate issuance wizard, browser plugin handshake, and CA portal authentication) is an OPAQUE system. It is documented as a scenario, not a mock. See `docs/scenarios/npki_portal_session.md`.

## What this mock reproduces

- `load_p12(path, password)` — loads a PKCS#12 bundle (.pfx/.p12) and extracts the X.509 certificate and private key, mirroring PyPinkSign's `PinkSign.load_p12()` interface shape
- `sign_cms(data: bytes, p12_bundle)` — produces a PKCS#7 detached CMS SignedData structure (DER-encoded), matching the output shape expected by data.go.kr e-form submission endpoints
- `verify_cms(signed_data: bytes, cert: x509.Certificate) -> bool` — verifies a CMS detached signature, matching PyPinkSign's verification interface shape
- `seed_encrypt(plaintext: bytes, cert: x509.Certificate) -> bytes` — SEED-CBC encryption (Korean SEED algorithm, RFC 4269) for NPKI-protected channel setup; shape-mirrors PyPinkSign's `seed_encrypt()`
- Error types: `InvalidPasswordError`, `CertExpiredError`, `SignatureVerificationError` — matching PyPinkSign exception names

## What this mock deliberately does NOT reproduce

- Real private key material — the mock generates ephemeral test keys at startup using Python's `cryptography` library
- NPKI portal session, CA web portal interaction, or OTP-based certificate renewal — these are OPAQUE; see `docs/scenarios/npki_portal_session.md`
- YESSIGN / KOSCOM / NHN CA certificate chain validation — mock certificates are self-signed test artifacts
- VID (Virtual ID) derivation — the VID computation formula is not publicly documented; KOSMOS treats it as OPAQUE
- NPKI browser plugin protocol (ActiveX / NPAPI / native messaging) — out of scope for the harness layer

## Fixture recording approach

Because all crypto operations use standard RFC-defined formats (PKCS#7, PKCS#12, SEED), test fixtures can be generated deterministically without a real NPKI certificate:

1. Run `uv run python tests/fixtures/generate_npki_crypto_fixtures.py` — this generates a self-signed test certificate bundle, signs a canonical payload, and writes the DER output to `tests/fixtures/npki_crypto/`.
2. The fixture generation script is part of the test suite and runs in CI without any live dependency.
3. To add a new fixture (e.g., for an error path), add a generation function to the script and commit the output.

## Upstream divergence policy

The PKCS#7 and PKCS#12 wire formats are stable RFC standards and will not diverge. The SEED algorithm (RFC 4269) is frozen. PyPinkSign may change its Python interface in new releases — pin the PyPinkSign version referenced in `tests/fixtures/npki_crypto/meta.json` and review interface changes when upgrading.
