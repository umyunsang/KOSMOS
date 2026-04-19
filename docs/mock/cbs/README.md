# Mock: cbs

**Mirror axis**: byte
**Source reference**: 3GPP TS 23.041 v17.0.0 — "Technical realization of Cell Broadcast Service (CBS)" (https://www.3gpp.org/ftp/Specs/archive/23_series/23.041/)
**License**: 3GPP (public specification, freely available)
**Scope**: Reproduces the Cell Broadcast Service (CBS) message structure and delivery notification format for Korean emergency alerts (재난문자) in the Message Identifier range 4370–4385, as defined by 3GPP TS 23.041 and implemented by the Korean National Disaster Management Research Institute (NDMI) over the KPAS protocol; limited to the network-side delivery notification shape consumed by KOSMOS — does not reproduce the radio access network layer.

## What this mock reproduces

- CBS message structure per 3GPP TS 23.041 §9: `MessageIdentifier` (uint16), `SerialNumber` (uint16), `DataCodingScheme` (uint8), `MessageContent` (variable, up to 1395 octets)
- Korean emergency alert Message Identifier assignments:
  - 4370 (`0x1112`): Presidential Alert (국가위기경보)
  - 4371 (`0x1113`): Emergency Alert (긴급재난문자)
  - 4372–4383: Disaster type sub-ranges (storm, flood, fire, earthquake, tsunami, nuclear, etc.)
  - 4384 (`0x1120`): Safety guidance
  - 4385 (`0x1121`): Test message
- Data Coding Scheme: `0x11` (UCS-2, class 1 — immediate display on device) as used for Korean-language alerts
- KPAS HTTP delivery notification shape: `{ msgId, serialNo, areaCode, sendTime, messageContent, messageType }` (as documented in NDMI KPAS integration guide)
- Geographic area code (`areaCode`) field: 8-digit code matching Korean administrative division codes

## What this mock deliberately does NOT reproduce

- LTE/5G radio broadcast scheduling or cell-tower coverage logic
- KPAS authentication credentials or HMAC-signed webhook delivery (mock accepts unauthenticated POST)
- SMS fallback path (P2P SMS delivery of alert content) — this is a separate delivery channel
- Real geographic targeting — mock delivers to all registered area codes regardless of zone

## Fixture recording approach

CBS messages have a fully public wire format defined by 3GPP TS 23.041. Fixtures are generated from the spec directly:

1. Run `uv run python tests/fixtures/generate_cbs_fixtures.py` — produces binary CBS PDUs and JSON KPAS notification objects for each of the 16 Message Identifiers (4370–4385) across three severity levels.
2. All fixture data uses synthetic Korean text content (no real emergency alert content is embedded).
3. Fixtures are committed under `tests/fixtures/cbs/` and replayed byte-for-byte by the mock server.

To add a fixture for a new Message Identifier (if NDMI extends the range):
1. Update `generate_cbs_fixtures.py` with the new `MessageIdentifier` value.
2. Re-run generation and commit.
3. Open a PR with label `mock-drift` and update the range in this README.

## Upstream divergence policy

3GPP TS 23.041 is a stable standard; the CBS message format does not change between 3GPP releases. The KPAS notification JSON shape may change when NDMI updates the KPAS integration guide — monitor NDMI API changelog. The `kpas_guide_version` field in `tests/fixtures/cbs/meta.json` records the KPAS guide version the fixture was built against.
