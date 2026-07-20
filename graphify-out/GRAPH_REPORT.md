# Graph Report - .  (2026-07-20)

## Corpus Check
- Corpus is ~7,986 words - fits in a single context window. You may not need a graph.

## Summary
- 89 nodes · 159 edges · 10 communities (7 shown, 3 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 12 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- A2A & FastAPI Integration
- Token Compression
- Configuration System
- Documentation & Providers
- Circuit Breaker State
- Tier & Resolution
- Health & Breaker Logic
- CLI & Router Core
- Chat & Token Counting
- Landing Page

## God Nodes (most connected - your core abstractions)
1. `Router` - 21 edges
2. `ProviderConfig` - 13 edges
3. `Compressor` - 12 edges
4. `Tier` - 11 edges
5. `load_config()` - 8 edges
6. `create_app()` - 8 edges
7. `CircuitState` - 8 edges
8. `get_agent_card()` - 5 edges
9. `count_tokens_approx()` - 5 edges
10. `resolve_model_chain()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `OpenRouter Provider Config` --conceptually_related_to--> `AI Gateway Concept`  [INFERRED]
  config.yaml → README.md
- `Python Dependencies` --conceptually_related_to--> `AI Gateway Concept`  [INFERRED]
  requirements.txt → README.md
- `Chat Interface` --conceptually_related_to--> `AI Gateway Concept`  [INFERRED]
  web/static/dashboard.html → README.md
- `CircuitState` --uses--> `Compressor`  [INFERRED]
  kopru/router.py → kopru/compression.py
- `Router` --uses--> `Compressor`  [INFERRED]
  kopru/router.py → kopru/compression.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-Provider Gateway Architecture** — readme_ai_gateway, readme_provider_fallback, config_openrouter, config_ollama, config_opencode_zen [INFERRED 0.85]

## Communities (10 total, 3 thin omitted)

### Community 0 - "A2A & FastAPI Integration"
Cohesion: 0.18
Nodes (14): FastAPI, get_agent_card(), handle_a2a_request(), Any, A2A Agent Card — başka ajanların Köprü'yü keşfetmesi için., A2A JSON-RPC 2.0 handler (basit)., load_catalog(), OmniRoute'tan alınan 277 provider kataloğunu yükler.     Dönüş: {"providers": {i (+6 more)

### Community 1 - "Token Compression"
Cohesion: 0.16
Nodes (8): Compressor, count_tokens_approx(), Mesaj dizisini sıkıştırır.      Stratejiler:       - none:    sıkıştırma yok, messages: [{"role": ..., "content": ...}, ...]         summarizer: optional call, Summarizer yoksa basit çıkarım: kullanıcı sorularını listele., Yaklaşık token sayısı (~4 char/token)., Yönlendirme istatistikleri., RouteStats

### Community 2 - "Configuration System"
Cohesion: 0.24
Nodes (10): _default_from_env(), _inject_env_keys(), load_config(), ProviderConfig, İstenen modeli içeren provider'ı bulur, fallback zinciri üretir.     Dönüş: [(ba, Tek bir AI sağlayıcı yapılandırması., config.yaml yükler. Bulunamazsa env'den varsayılan üretir.     Dönüş: {"provider, YAML'daki ${ENV_VAR} gösterimlerini gerçek değerle değiştir. (+2 more)

### Community 3 - "Documentation & Providers"
Cohesion: 0.17
Nodes (13): Ollama Provider Config, OpenCode Zen Provider Config, OpenRouter Provider Config, Köprü Configuration, A2A Agent-to-Agent Protocol, AI Gateway Concept, Köprü README, MCP Model Context Protocol (+5 more)

### Community 4 - "Circuit Breaker State"
Cohesion: 0.29
Nodes (3): CircuitState, Streaming sohbet — auto-fallback + circuit breaker + compression., Circuit breaker durumu (OmniRoute degradation.ts esinli).

### Community 5 - "Tier & Resolution"
Cohesion: 0.33
Nodes (5): Enum, Fitness tier — OmniRoute pipeline.ts ile aynı mantık., Tag'a göre fitness tier seç (code → best-reasoning, simple → cheapest)., Tier, str

### Community 7 - "CLI & Router Core"
Cohesion: 0.50
Nodes (3): main(), OpenAI uyumlu çoklu-provider router (OmniRoute benzeri)., Router

## Knowledge Gaps
- **6 isolated node(s):** `Provider Fallback Mechanism`, `Ollama Provider Config`, `OpenCode Zen Provider Config`, `Python Dependencies`, `GitHub Pages Landing` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Router` connect `CLI & Router Core` to `A2A & FastAPI Integration`, `Token Compression`, `Configuration System`, `Circuit Breaker State`, `Tier & Resolution`, `Health & Breaker Logic`, `Chat & Token Counting`?**
  _High betweenness centrality (0.247) - this node is a cross-community bridge._
- **Why does `Compressor` connect `Token Compression` to `Configuration System`, `Circuit Breaker State`, `Tier & Resolution`, `CLI & Router Core`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Why does `ProviderConfig` connect `Configuration System` to `Token Compression`, `Circuit Breaker State`, `Tier & Resolution`, `CLI & Router Core`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Router` (e.g. with `Compressor` and `ProviderConfig`) actually correct?**
  _`Router` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ProviderConfig` (e.g. with `CircuitState` and `Router`) actually correct?**
  _`ProviderConfig` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `Compressor` (e.g. with `CircuitState` and `Router`) actually correct?**
  _`Compressor` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Tier` (e.g. with `Compressor` and `ProviderConfig`) actually correct?**
  _`Tier` has 2 INFERRED edges - model-reasoned connections that need verification._