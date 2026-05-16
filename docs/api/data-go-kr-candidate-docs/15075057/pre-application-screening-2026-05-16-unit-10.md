# Pre-Application Screening: Unit 10

- Dataset: `15075057`
- Title: `식품의약품안전처_의약품개요정보(e약은요)`
- Portal URL: `https://www.data.go.kr/data/15075057/openapi.do`
- Provider: `식품의약품안전처`
- Classification: `보건 - 식품의약안전`
- Candidate adapter id: `mfds_easy_drug_info_lookup`
- Candidate primitive: `lookup`
- Screening result: pass

## UMMAYA Fit

This API is a strong UMMAYA candidate because citizens frequently ask practical medication-safety questions in natural language. It covers general OTC medicine overview data including company name, product name, item sequence code, efficacy, usage method, warnings, precautions, interactions, side effects, storage method, open date, update date, and pill image URL.

Natural-language query mapping:

- `타이레놀 효능이랑 복용법 알려줘.` -> search by `itemName`, return `efcyQesitm` and `useMethodQesitm`.
- `이 약 먹을 때 같이 먹으면 안 되는 음식이나 약 있어?` -> search by product name or `itemSeq`, return `intrcQesitm` and warning fields.
- `이 일반의약품 부작용 뭐야?` -> return `seQesitm` with a medical-disclaimer style response and source citation.
- `이 약은 어떻게 보관해야 해?` -> return `depositMethodQesitm`.

Expected use frequency: high. Medication questions are common, recurring, and citizen-facing. The adapter should be framed as official information lookup, not diagnosis or personal medical advice.

## Contract Notes Before Application

- Base URL: `http://apis.data.go.kr/1471000/DrbEasyDrugInfoService`
- Operation: `/getDrbEasyDrugList`
- Request parameters documented by the portal/DOCX: `ServiceKey`, `pageNo`, `numOfRows`, `entpName`, `itemName`, `itemSeq`, `efcyQesitm`, `useMethodQesitm`, `atpnWarnQesitm`, `atpnQesitm`, `intrcQesitm`, `seQesitm`, `depositMethodQesitm`, `openDe`, `updateDe`, `type`.
- Main response fields: `entpName`, `itemName`, `itemSeq`, `efcyQesitm`, `useMethodQesitm`, `atpnWarnQesitm`, `atpnQesitm`, `intrcQesitm`, `seQesitm`, `depositMethodQesitm`, `openDe`, `updateDe`, `itemImage`.
- Development traffic shown by portal: `10,000`.
- Approval shown by portal: automatic approval.

## Application Purpose

`UMMAYA R&D. Citizen medication information lookup adapter for OTC drug efficacy, usage, warnings, interactions, side effects, storage, and pill image answers using official MFDS e약은요 data. No diagnosis or resale.`
