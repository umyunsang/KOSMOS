# Scenario: KEC (한국전자인증) XML Digital Signature

**Why this is a scenario, not a mock**: The Korea Electronic Certification Authority (한국전자인증, KEC) XML digital signature workflow is not publicly reproducible. The XSD schema for KEC-specific signature extension elements and the public signing keys used by the KEC Timestamp Authority (TSA) and OCSP responder are not disclosed outside of licensed KEC integration agreements. Additionally, KEC's proprietary `SignedInfo` canonicalization profile (a variant of Canonical XML 1.0) includes undocumented normalization steps that cannot be reverse-engineered without access to the KEC SDK source code, which is distributed under a commercial license and is not open source.

## Journey overview

A business user uses KOSMOS to submit a legally binding electronic document — for example, an e-procurement bid (전자조달 입찰) or a regulatory filing — that requires a KEC-qualified XML digital signature (XML 전자서명). The journey proceeds as follows:

1. The business user requests a document submission requiring a KEC signature via the KOSMOS TUI.
2. KOSMOS resolves the required document schema from the relevant procurement portal or regulatory authority (this catalogue lookup is handled by `lookup` against a public API — mockable).
3. KOSMOS assembles the XML document payload in the required schema, annotating it with the required `ds:Signature` placeholder element per W3C XML Signature Syntax and Processing (XMLDSIG) 1.1.
4. KOSMOS invokes the `delegate` primitive to hand off the unsigned XML to the KEC signature service.
5. The KEC service receives the document, computes the `SignedInfo` digest using the KEC-specific canonicalization profile, requests the business user's certificate from the KEC-registered HSM, signs the document, and appends a KEC Timestamp Authority (TSA) timestamp token.
6. The KEC service returns the fully signed XML document (DER-encoded `ds:SignatureValue` + TSA token).
7. KOSMOS records the signed document reference (hash of the signed XML, not the document content) in the `ToolCallAuditRecord` and presents the outcome to the business user.

## KOSMOS ↔ real system handoff point

The handoff occurs at step 4: when KOSMOS calls `delegate(tool_id="kec_xml_sign", params={"unsigned_xml": ..., "cert_serial": ..., "signing_profile": ...})`.

At this point:
- KOSMOS has assembled a valid XML document payload conforming to the target schema.
- KOSMOS has resolved the business user's KEC certificate serial number from their NPKI certificate bundle (the PKCS#12 load step uses `docs/mock/npki_crypto`; the KEC-specific fields of the certificate are opaque at this layer).
- The `delegate` call crosses into the KEC signature service endpoint over a TLS channel with a KEC-issued server certificate (PKI chain validation required; root CA is the KEC Root CA, not a public WebPKI CA).
- KOSMOS records a `ToolCallAuditRecord` with `is_irreversible=True` before the handoff (a submitted signed document cannot be unsigned).
- On success: KOSMOS receives the signed XML and stores only the SHA-256 hash of the signed document in the audit record (not the document content itself, to minimise PIPA exposure).
- On failure: KOSMOS records the KEC error code and message (`{ kec_error_code, kec_error_message }`) in the audit record and presents a human-readable failure message.

KOSMOS does not retry a failed signature request automatically — the business user must re-initiate.

## What KOSMOS does on our side

- Assembles the unsigned XML document payload from public schema definitions (fully mockable for the document assembly layer).
- Resolves the certificate serial number from the NPKI PKCS#12 bundle using the `npki_crypto` mock layer.
- Emits a `ToolCallAuditRecord` with `is_irreversible=True` and `pipa_class="business_confidential"` before the handoff.
- Records only the SHA-256 hash of the successfully signed document — never the document content.
- Presents KEC error codes in human-readable Korean using a public KEC error code table (this mapping table is published in the KEC integration documentation and is mockable).

## What KOSMOS deliberately does NOT do (harness discipline)

- KOSMOS does not implement the KEC-specific XML canonicalization profile — this is the OPAQUE boundary.
- KOSMOS does not implement KEC's TSA timestamp token format — treated as opaque binary.
- KOSMOS does not access or cache the business user's private key material — key storage remains in the KEC HSM.
- KOSMOS does not expose the KEC integration credentials in source code, configuration, or logs.
- KOSMOS does not validate the returned signed XML using the KEC-specific OCSP responder — that validation is the responsibility of the document recipient's system.

---

*Promoted to mock on <date>, tracked by #<issue>* — replace this line when KEC publishes a reference XSD and open OCSP endpoint that allow a shape-axis mock to be constructed.
