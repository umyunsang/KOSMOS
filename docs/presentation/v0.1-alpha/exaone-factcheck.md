# K-EXAONE Fact-Check Report

**Date:** 2026-04-26
**Purpose:** Verify exact model names, specs, and availability for KOSMOS presentation materials
**Method:** Direct WebFetch from HuggingFace model pages and FriendliAI; no inference or guesswork

---

## 1. LGAI-EXAONE HuggingFace Organization — Full Model Lineup

**Source:** https://huggingface.co/LGAI-EXAONE (fetched 2026-04-26)

Total published models: **46** (page displays top results; full list requires pagination)

### Confirmed visible models by series:

| Model Name | Type | HF-reported Size | Last Updated |
|---|---|---|---|
| EXAONE-4.5-33B | Image-Text-to-Text (VLM) | 34B | ~11 days ago (≈Apr 15, 2026) |
| EXAONE-4.5-33B-FP8 | Image-Text-to-Text | 34B | ~11 days ago |
| EXAONE-4.5-33B-AWQ | Image-Text-to-Text | 8B (quantized) | ~4 days ago |
| EXAONE-4.5-33B-GGUF | Image-Text-to-Text | 33B | ~12 days ago |
| K-EXAONE-236B-A23B | Text Generation (MoE) | 237B | Feb 24, 2026 |
| K-EXAONE-236B-A23B-FP8 | Text Generation (MoE) | 237B | Feb 24, 2026 |
| EXAONE-Deep-32B-AWQ | Text Generation | 32B | Feb 6, 2026 |
| EXAONE-Deep-2.4B-AWQ | Text Generation | 2B | Feb 6, 2026 |
| EXAONE-Path-2.5 | Specialized (pathology) | N/A | Mar 10, 2026 |
| EXAONE-Path-2.0-rev-EGFR | Specialized (pathology) | N/A | ~19 days ago |

> **Note:** K-EXAONE-236B-A23B and EXAONE-3.5-* series are present among the 46 total models but
> were not shown in the paginated top results (sorted by recent activity). Both were individually
> confirmed via direct URL fetch (see Section 2 and Section 3 below).

---

## 2. K-EXAONE Series — Detailed Verification

### 2a. K-EXAONE-236B-A23B

**Source:** https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B (fetched 2026-04-26)

**VERDICT: MODEL EXISTS AND IS CONFIRMED.**

| Field | Value |
|---|---|
| Exact HF model card title | `K-EXAONE-236B-A23B` |
| HuggingFace URL | https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B |
| Parameters (without embeddings) | 30.95B |
| License | EXAONE AI Model License Agreement 1.2 - NC |
| Context window | **131,072 tokens (128K)** |
| Release date | July 15, 2025 (arXiv: 2507.11407) |
| Architecture | Dense causal LM; 64 layers; GQA 40Q-heads / 8 KV-heads |
| Hybrid Attention | Sliding window (local) + Global, 3:1 ratio |
| Vocab size | 102,400 |
| Data type | BF16 |
| Tool/Function calling | Yes — native agentic tool use with function schema |
| Multilingual | English, Korean, Spanish |

**Benchmark scores (32B Reasoning Mode):**

| Benchmark | Score |
|---|---|
| KMMLU-Pro (Korean) | 67.7 |
| KMMLU-Redux (Korean) | 72.7 |
| KSM (Korean) | 87.6 |
| Ko-LongBench (Korean) | 76.9 |
| MMLU-Redux | 92.3 |
| MMLU-Pro | 81.8 |
| GPQA-Diamond | 75.4 |
| AIME 2025 | 85.3 |
| LiveCodeBench v5 | 72.6 |
| IFEval | 83.7 |

### 2b. EXAONE-4.0-1.2B

**Source:** https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-1.2B (fetched 2026-04-26)

**VERDICT: MODEL EXISTS AND IS CONFIRMED.**

| Field | Value |
|---|---|
| Exact HF model card title | `EXAONE-4.0-1.2B` |
| HuggingFace URL | https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-1.2B |
| Parameters | 1.07B (1.28B with embeddings) |
| License | EXAONE AI Model License Agreement 1.2 - NC |
| Context window | **65,536 tokens (64K)** |
| Release date | July 15, 2025 (same arXiv: 2507.11407) |
| Architecture | 30 layers; GQA 32Q-heads / 8 KV-heads |
| Tool/Function calling | Yes |
| Multilingual | English, Korean, Spanish |

**K-EXAONE series conclusion:** Two variants exist: **1.2B and 32B**. No 7B variant.
The KOSMOS-referenced model `LGAI-EXAONE/K-EXAONE-236B-A23B` is real and correctly named.

---

## 3. EXAONE 3.5 Series — Cross-Reference

**Source:** https://huggingface.co/LGAI-EXAONE/EXAONE-3.5-32B-Instruct (fetched 2026-04-26)

| Field | Value |
|---|---|
| Exact HF model card title | `EXAONE-3.5-32B-Instruct` |
| HuggingFace URL | https://huggingface.co/LGAI-EXAONE/EXAONE-3.5-32B-Instruct |
| Parameters (without embeddings) | 30.95B |
| License | EXAONE AI Model License Agreement **1.1** - NC |
| Context window | **32,768 tokens (32K)** — half of K-EXAONE |
| Release date | December 6, 2024 (arXiv: 2412.04862) |
| Variants | 2.4B, 7.8B, 32B |

**Conclusion:** EXAONE 3.5 is the predecessor series. K-EXAONE-236B-A23B doubles the context window
(128K vs 32K) and adds hybrid reasoning. KOSMOS should NOT reference EXAONE 3.5 as the current model.

---

## 4. FriendliAI Serverless — K-EXAONE Model Availability

**Sources:**
- https://friendli.ai/blog/lg-ai-research-partnership-exaone-4.0 (fetched 2026-04-26)
- https://friendli.ai/models/LGAI-EXAONE/K-EXAONE-236B-A23B (fetched 2026-04-26)
- Search result: https://friendli.ai/suite/~/serverless-endpoints/LGAI-EXAONE/K-EXAONE-236B-A23B/overview

### Confirmed FriendliAI Serverless models:

| Model | FriendliAI Serverless model ID | Pricing (Input / Output per 1M tokens) |
|---|---|---|
| K-EXAONE 32B | `LGAI-EXAONE/K-EXAONE-236B-A23B` | Not confirmed from public docs |
| K-EXAONE 236B-A23B | `LGAI-EXAONE/K-EXAONE-236B-A23B` | $0.20 input / $0.80 output |

**API endpoint (OpenAI-compatible):**
```
Base URL: https://api.friendli.ai/serverless/v1
Auth header: Authorization: Bearer $FRIENDLI_TOKEN
model field: "LGAI-EXAONE/K-EXAONE-236B-A23B"
```

**Important clarification:** The FriendliAI suite page URL for K-EXAONE-236B-A23B was confirmed at
`https://friendli.ai/suite/~/serverless-endpoints/LGAI-EXAONE/K-EXAONE-236B-A23B/overview` but requires
login — the page redirected to authentication. The model ID `LGAI-EXAONE/K-EXAONE-236B-A23B` was
independently confirmed from the FriendliAI partnership blog post and HuggingFace blog post
(https://huggingface.co/blog/FriendliAI/lg-ai-research-partnership-exaone-4).

**VERDICT:** K-EXAONE-236B-A23B is confirmed available on FriendliAI Serverless with model ID
`LGAI-EXAONE/K-EXAONE-236B-A23B`. K-EXAONE-236B-A23B is also available with confirmed pricing.

---

## 5. K-EXAONE Verification

**Sources:**
- https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B (fetched 2026-04-26)
- https://www.prnewswire.com/news-releases/lg-rolls-outs-k-exaone-... (PR Newswire, via search)
- https://github.com/LG-AI-EXAONE/K-EXAONE (GitHub official repo, via search)

**VERDICT: "K-EXAONE" IS A REAL, OFFICIAL LG AI RESEARCH MODEL NAME.**

| Field | Value |
|---|---|
| Full model name | K-EXAONE-236B-A23B |
| HuggingFace URL | https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B |
| GitHub official repo | https://github.com/LG-AI-EXAONE/K-EXAONE |
| License | K-EXAONE AI Model License Agreement (separate from K-EXAONE license) |
| Architecture | Mixture of Experts (MoE): 236B total, **23B active** during inference |
| Experts | 128 total, 8 activated per forward pass + 1 shared expert |
| Context window | **262,144 tokens (256K)** |
| Vocab size | 153,600 (SuperBPE redesign) |
| Announcement | January 12, 2026 (arXiv: 2601.01739, published Jan 5, 2026) |
| Knowledge cutoff | December 2024 |
| Languages | Korean, English, Spanish, German, Japanese, Vietnamese (6 languages) |
| MTP | Multi-Token Prediction — ~1.5x throughput boost via self-speculative decoding |

**What "K" means:** "K" = **Korea**. LG AI Research officially named it as South Korea's
homegrown frontier AI model to compete with US/Chinese frontier models. PR Newswire headline:
"LG Rolls outs 'K-EXAONE': South Korea Joins the Global Frontier AI Race with World-Class AI Model"

**Korean benchmark scores:**

| Benchmark | Score |
|---|---|
| KMMLU-Pro | 67.3 |
| KoBALT | 61.8 |
| CLIcK | 83.9 |
| HRM8K | 90.9 |
| Ko-LongBench | 86.8 |

**K-EXAONE vs K-EXAONE comparison:**

| | K-EXAONE-236B-A23B | K-EXAONE-236B-A23B |
|---|---|---|
| Architecture | Dense | MoE |
| Total params | 30.95B | 236B |
| Active params | 30.95B | 23B |
| Context | 128K | 256K |
| Released | Jul 2025 | Jan 2026 |
| Lang support | 3 | 6 |
| License type | K-EXAONE 1.2-NC | K-EXAONE (separate) |

---

## 6. EXAONE 4.5 — Bonus Finding (Post-Knowledge-Cutoff Model)

**Source:** https://www.prnewswire.com/news-releases/lg-reveals-next-gen-multimodal-ai-exaone-4-5-* (via search)
**HF URL:** https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B

| Field | Value |
|---|---|
| Release date | **April 9, 2026** |
| Architecture | Vision-Language Model (VLM) — image + text |
| Parameters | 33B (LLM backbone) + 1.29B vision encoder |
| Context window | 262,144 tokens (256K) |
| Languages | Korean, English, Spanish, German, Japanese, Vietnamese |

**Note for KOSMOS:** EXAONE 4.5 is a VLM released AFTER the agent's knowledge cutoff (Aug 2025).
It is the newest LGAI-EXAONE model as of this fact-check date (2026-04-26). KOSMOS currently
targets K-EXAONE-236B-A23B which predates it; the codebase may want to evaluate migration.

---

## 7. KOSMOS Presentation Correction Summary

### Current KOSMOS codebase expression (from AGENTS.md / CLAUDE.md):
```
FriendliAI Serverless + K-EXAONE (LGAI-EXAONE/K-EXAONE-236B-A23B)
```

### Fact-check verdict on each element:

| Claim | Status | Correction |
|---|---|---|
| `K-EXAONE-236B-A23B` exists on HuggingFace | CONFIRMED | No correction needed |
| `LGAI-EXAONE/K-EXAONE-236B-A23B` is the FriendliAI serverless model ID | CONFIRMED | No correction needed |
| "K-EXAONE" is a real LG AI Research official term | CONFIRMED | K-EXAONE = K-EXAONE-236B-A23B, a separate MoE model — NOT the same as K-EXAONE-236B-A23B |
| "32B exists" | CONFIRMED | K-EXAONE-236B-A23B is real at 30.95B params |

### CRITICAL FINDING — Naming Ambiguity:

The KOSMOS codebase combines "K-EXAONE" with "K-EXAONE-236B-A23B" as if they are the same model.
**They are not.** K-EXAONE refers to `K-EXAONE-236B-A23B` (a 236B MoE model released Jan 2026).
K-EXAONE-236B-A23B is a separate dense 32B model released July 2025.

**Recommended correction for KOSMOS presentation materials:**

Option A — If using the 32B model:
```
Provider: FriendliAI Serverless
Model: LGAI-EXAONE/K-EXAONE-236B-A23B
Parameters: 30.95B (dense)
Context: 128K tokens
Released: July 15, 2025
```

Option B — If intending the frontier Korean model:
```
Provider: FriendliAI Serverless
Model: LGAI-EXAONE/K-EXAONE-236B-A23B
Parameters: 236B total / 23B active (MoE)
Context: 256K tokens
Released: January 2026
Pricing: $0.20/1M input, $0.80/1M output
```

---

## 8. Sources Index

| # | Description | URL |
|---|---|---|
| 1 | LGAI-EXAONE HF org page | https://huggingface.co/LGAI-EXAONE |
| 2 | K-EXAONE-236B-A23B model card | https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B |
| 3 | EXAONE-4.0-1.2B model card | https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-1.2B |
| 4 | EXAONE-3.5-32B-Instruct model card | https://huggingface.co/LGAI-EXAONE/EXAONE-3.5-32B-Instruct |
| 5 | K-EXAONE-236B-A23B model card | https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B |
| 6 | K-EXAONE-236B-A23B on FriendliAI | https://friendli.ai/models/LGAI-EXAONE/K-EXAONE-236B-A23B |
| 7 | FriendliAI + K-EXAONE partnership blog | https://friendli.ai/blog/lg-ai-research-partnership-exaone-4.0 |
| 8 | FriendliAI + K-EXAONE day-0 blog | https://friendli.ai/blog/k-exaone-on-serverless |
| 9 | HF blog: FriendliAI x K-EXAONE | https://huggingface.co/blog/FriendliAI/lg-ai-research-partnership-exaone-4 |
| 10 | K-EXAONE GitHub official repo | https://github.com/LG-AI-EXAONE/K-EXAONE |
| 11 | EXAONE 4.5 PR Newswire | https://www.prnewswire.com/news-releases/lg-reveals-next-gen-multimodal-ai-exaone-4-5-302736993.html |
| 12 | EXAONE-4.5-33B HF model card | https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B |
| 13 | FriendliAI serverless K-EXAONE-236B-A23B overview | https://friendli.ai/suite/~/serverless-endpoints/LGAI-EXAONE/K-EXAONE-236B-A23B/overview |
