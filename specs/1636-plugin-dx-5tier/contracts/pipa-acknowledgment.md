# Contract — PIPA §26 Trustee Acknowledgment

**Source-of-truth file**: `docs/plugins/security-review.md` (sections between `<!-- CANONICAL-PIPA-ACK-START -->` and `<!-- CANONICAL-PIPA-ACK-END -->`).
**Hash module**: `src/kosmos/plugins/canonical_acknowledgment.py` exports `CANONICAL_ACKNOWLEDGMENT_SHA256: str` computed at import time.
**Manifest field**: `PluginManifest.pipa_trustee_acknowledgment` (nested `PIPATrusteeAcknowledgment` model).

## Canonical text format

```markdown
<!-- CANONICAL-PIPA-ACK-START -->

본 플러그인의 기여 조직(이하 "수탁자")은 「개인정보 보호법」 제26조 및 같은 법
시행령 제28조에 따른 개인정보 처리 위탁의 수탁자로서 다음 의무를 인지하고
이행하기로 동의합니다.

1. 위탁업무의 목적과 범위 내에서만 개인정보를 처리합니다.
2. 위탁업무 처리 목적 달성에 필요한 최소한의 개인정보만을 수집·이용합니다.
3. 개인정보의 안전성 확보를 위한 기술적·관리적 조치를 이행합니다.
4. 재위탁(下수탁)은 KOSMOS 운영자(위탁자)의 사전 서면 동의 없이 수행하지 않습니다.
5. 개인정보의 처리 현황 및 안전성 확보 조치 이행 여부에 대한 KOSMOS 운영자의
   감독에 협조합니다.
6. 위탁업무 종료 시 개인정보를 지체 없이 파기하고 그 결과를 KOSMOS 운영자에게
   서면으로 통보합니다.
7. 본 의무를 위반하여 정보주체에게 손해가 발생한 경우 그 손해를 배상할 책임이
   있음을 확인합니다.

수탁자는 본 acknowledgment 의 SHA-256 해시값을 플러그인 manifest 에 기록함으로써
위 의무에 동의함을 표시합니다.

<!-- CANONICAL-PIPA-ACK-END -->
```

## Hash computation algorithm

```python
def _extract_canonical_text(security_review_md: str) -> str:
    """Extract the canonical block from docs/plugins/security-review.md."""
    start = security_review_md.find("<!-- CANONICAL-PIPA-ACK-START -->")
    end = security_review_md.find("<!-- CANONICAL-PIPA-ACK-END -->")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError("canonical PIPA acknowledgment markers not found in docs/plugins/security-review.md")
    raw = security_review_md[start + len("<!-- CANONICAL-PIPA-ACK-START -->") : end]
    return raw.strip().replace("\r\n", "\n")

def _compute_canonical_hash(canonical_text: str) -> str:
    return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()

# Module-level constant
CANONICAL_ACKNOWLEDGMENT_SHA256 = _compute_canonical_hash(
    _extract_canonical_text(_load_security_review_md())
)
```

## Manifest field shape

```yaml
# manifest.yaml excerpt
processes_pii: true
pipa_trustee_acknowledgment:
  trustee_org_name: "Seoul Metropolitan Government - Open Data Plaza"
  trustee_contact: "open-data@seoul.go.kr"
  pii_fields_handled:
    - station_code
  legal_basis: "「개인정보 보호법」 제15조 제1항 제1호 (정보주체의 동의)"
  acknowledgment_sha256: "<64-hex SHA-256 of canonical text>"
```

## Validation rules

1. Hash MUST equal `CANONICAL_ACKNOWLEDGMENT_SHA256`. Any drift (text edit + forgotten hash refresh) fails CI.
2. `trustee_org_name` and `trustee_contact` MUST be non-empty strings (no placeholder values like "TBD" or "Unknown" — though empty-string check is the only mechanical enforcement; a soft "no TBD" lint may be added later).
3. `pii_fields_handled` MUST be a non-empty list.
4. `legal_basis` MUST be a non-empty string. (Free-text; manual review covers content quality.)
5. When `processes_pii: false`, the entire `pipa_trustee_acknowledgment` block MUST be absent (`null` in JSON Schema).

## Drift detection (Deferred)

When the legal team approves a new acknowledgment text, the canonical SHA-256 changes. All previously merged plugins now have stale hashes. The deferred `plugin-acknowledgment-audit.yml` workflow scans the catalog and lists affected plugins for re-acknowledgment. Tracked as the OOS-table row 7 (NEEDS TRACKING).

## Operations

- **Updating the canonical text**: requires legal review. Edit `docs/plugins/security-review.md` between the markers; bump `docs/plugins/security-review.md` revision history; deploy. The new hash is computed automatically at next backend boot.
- **Migrating existing plugins**: each affected plugin author opens a one-line PR updating their manifest's `acknowledgment_sha256`; the validation workflow accepts the new hash; merge. No code change required.
- **Hash exposure**: the canonical hash is published verbatim at the top of `docs/plugins/security-review.md` (e.g., "Current canonical SHA-256: `abc123...`") and printed by `kosmos plugin init` immediately before the contributor confirms acknowledgment.

## Reference

- Korea PIPA (개인정보 보호법): https://www.law.go.kr/법령/개인정보보호법
- PIPA §26 (위탁): https://www.law.go.kr/법령/개인정보보호법/제26조
- PIPA Enforcement Decree §28 (위탁자의 의무): https://www.law.go.kr/법령/개인정보보호법시행령/제28조
- Memory `project_pipa_role` (KOSMOS PIPA stance — trustee by default, controller carve-out only at LLM synthesis step)
