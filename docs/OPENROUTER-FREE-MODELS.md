# OpenRouter Free Models

Generated: 2026-10-26  
Source: `GET https://openrouter.ai/api/v1/models` (records with `id` ending in `:free`)  
"Released" date = OpenRouter `created` timestamp (matches "Released <date>" shown on each model's web page)

Total `:free` models at time of generation: **17** (sorted by release date, newest first)

## Refresh the list

No scraping required. The data comes from OpenRouter's public model registry, so this doc can be regenerated at any time with:

```bash
curl -s 'https://openrouter.ai/api/v1/models' | python3 -c "
import json, sys, datetime
data = json.load(sys.stdin)['data']
free = sorted([m for m in data if m['id'].endswith(':free')],
              key=lambda m: m.get('created', 0), reverse=True)
for m in free:
    print(m['id'], '|', m.get('created'))
"
```

## Model list

| Released | Model | Context | Input → Output | Reasoning | Max output tokens | Expires | Notes |
|---|---|---|---|---|---|---|---|
| 2026-10-21 | `recursive/flint-v1.0:free` | 262,144 | text → text | **mandatory** | 235,929 | — | Recursive: Flint. Open-weight MoE (~2.5B active / 40B total). Reasoning can *not* be disabled — expect silent thinking tokens to consume your output budget. Best for: coding agents. |
| 2026-10-16 | `xingchen-agi/xing4.0-29b-a4b:free` | 262,144 | text → text | none | 235,929 | — | XingChen: Xing4.0 29B A4B. Best for: general text tasks. |
| 2026-10-15 | `nvidia/nemotron-3.5-super-vl:free` | 1,000,000 | text + image + video → text | on by default | 131,072 | — | NVIDIA: Nemotron 3.5 Super VL. Multimodal (text/image/video → text), hybrid Mamba-Transformer MoE (12B active / 120B total). Reasoning is on by default but can be turned off or given a token budget via `reasoning.max_tokens`. Best for: long-context agentic tasks, video/document understanding. |
| 2026-08-14 | `dots-studio/dots-3-note-preview:free` | 512,000 | text + image → text | none | 460,800 | 2026-12-31 | Dots Studio: Dots3-Note Preview. Free tier expires end of 2026. |
| 2026-08-11 | `liquid/lfm-2.5-2.6b:free` | 65,536 | text → text | **mandatory** | 8,192 | — | LiquidAI: LFM2.5-2.6B. Reasoning mandatory — small output budget (8,192 tokens). Best for: short reasoning/agent tasks. |
| 2026-08-11 | `nvidia/nemotron-3.5-lightning:free` | 1,000,000 | text → text | none | 65,536 | — | NVIDIA: Nemotron 3.5 Lightning. High-throughput free text model, 1M context. |
| 2026-07-30 | `thinkingmachines/inkling-small:free` | 1,048,576 | text + image + audio → text | none | 262,144 | — | Thinking Machines: Inkling Small. Multimodal (text/image/audio → text), 1M context. |
| 2026-07-21 | `poolside/laguna-s-2.1:free` | 262,144 | text → text | none | 32,768 | 2026-10-31 | Poolside: Laguna S 2.1. Free tier expires end of October 2026. |
| 2026-07-17 | `thinkingmachines/inkling:free` | 1,048,576 | text + image + audio → text | none | 262,144 | — | Thinking Machines: Inkling. Multimodal (text/image/audio → text), 1M context. |
| 2026-07-02 | `poolside/laguna-xs-2.1:free` | 262,144 | text → text | none | 32,768 | 2026-10-31 | Poolside: Laguna XS 2.1. Free tier expires end of October 2026. |
| 2026-06-17 | `cohere/north-mini-code:free` | 256,000 | text → text | none | 64,000 | — | Cohere: North Mini Code. Coding-focused. |
| 2026-06-04 | `nvidia/nemotron-3.5-content-safety:free` | 128,000 | text + image → text | none | 8,192 | — | NVIDIA: Nemotron 3.5 Content Safety. Classifier-style safety model, small output budget. Not a general-purpose generator. |
| 2026-06-04 | `nvidia/nemotron-3-ultra-550b-a55b:free` | 1,000,000 | text → text | none | 65,536 | — | NVIDIA: Nemotron 3 Ultra. 1M context free text model. |
| 2026-04-28 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | 256,000 | text + audio + image + video → text | none | 65,536 | — | NVIDIA: Nemotron 3 Nano Omni (reasoning). Multimodal omni model; 16K reasoning budget supported via `reasoning.enabled`. |
| 2026-04-03 | `google/gemma-4-26b-a4b-it:free` | 262,144 | image + text + video → text | none | 32,768 | — | Google: Gemma 4 26B A4B (instruct). Multimodal instruct model. |
| 2026-04-02 | `google/gemma-4-31b-it:free` | 262,144 | image + text + video → text | none | 32,768 | — | Google: Gemma 4 31B (instruct). Multimodal instruct model. |
| 2026-03-11 | `nvidia/nemotron-3-super-120b-a12b:free` | 262,144 | text → text | none | 235,929 | — | NVIDIA: Nemotron 3 Super. 120B-parameter open MoE (12B active), high max output. |

## Notes relevant to learn-jp

- **Reasoning models can silently burn your output budget.** `recursive/flint-v1.0:free` and `liquid/lfm-2.5-2.6b:free` have mandatory reasoning. `nvidia/nemotron-3.5-super-vl:free` has reasoning on by default but it *can* be capped with `reasoning.max_tokens` (verified empirically: without a cap, output can be 90% silent reasoning and return empty content; with `reasoning.max_tokens: 50` it produces usable Japanese text in ~130 tokens). See my earlier tests in this chat for details.
- **Max output tokens** here is the provider's advertised ceiling (`top_provider.max_completion_tokens`), not a guarantee — free endpoints can throttle or truncate lower.
- **Expiring free tiers:** Poolside Laguna models expire 2026-10-31; Dots3-Note Preview expires 2026-12-31. If you hardcode a free model as the pipeline default, prefer one without an expiration date.
- **Non-exhaustive:** OpenRouter also lists paid models and non-`:free` variants (e.g. `google/gemma-4-26b-a4b-it` without `:free`). This doc only covers the explicitly free tier as requested.
