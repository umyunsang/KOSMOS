# Evaluation Scenarios

Citizen request test scenarios for quantitative evaluation.

## Format

Each scenario is a JSON file:

```json
{
  "id": "S001",
  "category": "traffic_safety",
  "ministries": ["KOROAD", "KMA"],
  "query_ko": "내일 부산에서 서울 가는데, 안전한 경로 추천해줘",
  "query_en": "Recommend a safe route from Busan to Seoul tomorrow",
  "expected_apis": ["koroad_accident_info", "kma_weather_alert"],
  "expected_behavior": "fuse accident data + weather alerts → route recommendation",
  "difficulty": "medium",
  "requires_auth": false,
  "requires_pii": false,
  "phase": 1
}
```

## Scenario categories

| Category | Count target | Ministries involved |
|----------|-------------|-------------------|
| traffic_safety | 10 | KOROAD, KMA, MOLIT |
| emergency_care | 10 | 119, HIRA, MOHW |
| welfare_benefits | 10 | MOHW, Gov24 |
| residence_transfer | 10 | MOIS, MOLIT, NHIS |
| disaster_response | 10 | KMA, NEMA, local gov |
| **Total** | **50** | |
