#!/usr/bin/env python3
"""
Build the complete provider_catalog.py by reading the existing file
and injecting all missing providers from OmniRoute sources.
"""
import re, textwrap, sys

# ── Existing provider IDs (from current provider_catalog.py) ──────────────
EXISTING_IDS = {
    "openai", "anthropic", "google", "gemini", "deepseek", "mistral", "xai",
    "meta-llama", "cohere", "perplexity", "reka", "together", "groq",
    "fireworks", "cerebras", "nvidia", "nebius", "deepinfra", "sambanova",
    "lambda-ai", "huggingface", "replicate", "siliconflow", "hyperbolic",
    "baseten", "featherless-ai", "stability-ai", "black-forest-labs",
    "fal-ai", "ideogram", "leonardo", "recraft", "runwayml", "haiper",
    "suno", "udio", "elevenlabs", "deepgram", "assemblyai", "cartesia",
    "playht", "voyage-ai", "jina-ai", "nomic", "mixedbread", "azure-openai",
    "bedrock", "vertex", "cloudflare-ai", "databricks", "snowflake",
    "scaleway", "openrouter", "novita", "chutes", "aimlapi", "poe",
    "minimax", "kimi", "qianfan", "alibaba", "gigachat", "firecrawl",
    "serper", "brave-search", "exa", "tavily", "dify", "nlpcloud",
    "ollama", "llamafile", "lm-studio", "ai21", "upstage", "codestral",
    "venice", "nous-research", "arcee-ai", "liquid", "maritalk", "blackbox",
    "galadriel", "morph", "pioneer", "digitalocean", "pollinations",
    "topaz", "segmind", "v0-vercel", "gitlab",
}

# ── New providers to add ─────────────────────────────────────────────────
# Format: (id, alias, name, icon, color, textIcon, website, hasFree, freeNote, serviceKinds, category)

NEW_PROVIDERS = [
    # ═══ inference-hosts ═══
    ("openvecta", "OpenVecta", "OpenVecta", "vector_polygon", "#7C3AED", "OV", "https://openvecta.com", True, "Free credits on signup for OpenAI-compatible inference", ["chat", "completion", "embedding"], "inference-hosts"),
    ("ollama-cloud", "Ollama Cloud", "Ollama Cloud", "cloud", "#58A6FF", "OC", "https://ollama.com/settings/keys", True, "Free cloud inference tier", ["chat", "completion"], "inference-hosts"),
    ("github-models", "GitHub Models", "GitHub Models", "code", "#238636", "GH", "https://github.com/marketplace/models", True, "Free GPT-5, o-series, DeepSeek-R1, Llama 4 — GitHub account only", ["chat", "completion"], "inference-hosts"),
    ("nube", "Nube.sh", "Nube.sh", "cloud", "#2563EB", "NB", "https://nube.sh", False, "Requires API key — BYOK gateway", ["chat", "completion"], "inference-hosts"),
    ("nscale", "nScale", "nScale", "token", "#0891B2", "NS", "https://nscale.com", True, "$5 free credits on signup for inference testing", ["chat", "completion"], "inference-hosts"),
    ("publicai", "PublicAI", "PublicAI", "public", "#059669", "PA", "https://publicai.co", False, "Requires an API key — one-time signup credit, then paid", ["chat", "completion"], "inference-hosts"),
    ("friendliai", "FriendliAI", "FriendliAI", "handshake", "#EC4899", "FR", "https://friendli.ai", True, "Free tier for serverless inference", ["chat", "completion"], "inference-hosts"),
    ("wandb", "Weights & Biases", "Weights & Biases Inference", "monitoring", "#FFBE0B", "WB", "https://wandb.ai", False, "W&B Inference — pay-as-you-go", ["chat", "completion"], "inference-hosts"),
    ("inference-net", "Inference.net", "Inference.net", "dns", "#2563EB", "IN", "https://inference.net", True, "$25 free credits on signup plus research grants", ["chat", "completion"], "inference-hosts"),
    ("predibase", "Predibase", "Predibase", "deployed_code_history", "#0F766E", "PB", "https://predibase.com", False, "Deprecated — serving API discontinued (2026-06)", ["chat", "completion"], "inference-hosts"),
    ("bytez", "Bytez", "Bytez", "api", "#6366F1", "BZ", "https://bytez.com", True, "$1 free credits, refreshes every 4 weeks", ["chat", "completion"], "inference-hosts"),
    ("monsterapi", "MonsterAPI", "MonsterAPI", "cloud", "#EF4444", "MA", "https://monsterapi.ai", True, "One-time signup trial credits for decentralized GPU inference", ["chat", "completion"], "inference-hosts"),
    ("modelscope", "ModelScope", "ModelScope", "cloud", "#FF6A00", "MS", "https://modelscope.cn", True, "Free tier via ModelScope API-Inference", ["chat", "completion"], "inference-hosts"),
    ("byteplus", "BytePlus ModelArk", "BytePlus ModelArk", "cloud", "#2563EB", "BP", "https://console.byteplus.com/ark", True, "Free credits for new accounts", ["chat", "completion"], "inference-hosts"),

    # ═══ gateways ═══
    ("charm-hyper", "Charm Hyper", "Charm Hyper", "router", "#7C3AED", "CH", "https://hyper.charm.land", True, "100 free monthly Hypercredits on signup", ["chat", "completion"], "gateways"),
    ("agentrouter", "AgentRouter", "AgentRouter", "router", "#10B981", "AR", "https://agentrouter.org", True, "$200 free credits on signup — multi-model routing gateway", ["chat", "completion"], "gateways"),
    ("command-code", "Command Code", "Command Code", "terminal", "#111827", "CC", "https://commandcode.ai", False, "Command Code API — coding-focused gateway", ["chat", "completion", "code"], "gateways"),
    ("requesty", "Requesty", "Requesty", "router", "#6366F1", "RQ", "https://requesty.ai", True, "Free tier ~200 requests/day — multi-model routing (300+ models)", ["chat", "completion"], "gateways"),
    ("dgrid", "DGrid", "DGrid", "router", "#65A30D", "DG", "https://dgrid.ai", True, "Free Models Router: 10 RPM, 100 RPD", ["chat", "completion"], "gateways"),
    ("qiniu", "Qiniu", "Qiniu", "cloud", "#1E88E5", "QN", "https://www.qiniu.com", False, "Qiniu AI inference — BYOK gateway", ["chat", "completion"], "gateways"),
    ("orcarouter", "OrcaRouter", "OrcaRouter", "router", "#0891B2", "ORC", "https://www.orcarouter.ai", False, "OrcaRouter — OpenAI-compatible multi-model gateway", ["chat", "completion"], "gateways"),
    ("api-airforce", "Api.airforce", "Api.airforce", "flight", "#1E3A5F", "AF", "https://api.airforce", True, "55 free tier models including Grok-3, Claude 3.7, Qwen3", ["chat", "completion"], "gateways"),
    ("crof", "CrofAI", "CrofAI", "auto_awesome", "#0EA5E9", "CR", "https://crof.ai", False, "CrofAI gateway", ["chat", "completion"], "gateways"),
    ("bazaarlink", "BazaarLink", "BazaarLink", "storefront", "#6366F1", "BZ", "https://bazaarlink.ai", True, "Free tier: 4M tokens/day per account — zero-cost inference", ["chat", "completion"], "gateways"),
    ("synthetic", "Synthetic", "Synthetic", "verified_user", "#6366F1", "SY", "https://synthetic.new", False, "Synthetic gateway — passthrough models", ["chat", "completion"], "gateways"),
    ("kilo-gateway", "Kilo Gateway", "Kilo Gateway", "hub", "#617A91", "KG", "https://kilo.ai", False, "Kilo Gateway — multi-model passthrough", ["chat", "completion"], "gateways"),
    ("wafer", "Wafer AI", "Wafer AI", "layers", "#6366F1", "WF", "https://wafer.ai", False, "Wafer AI gateway", ["chat", "completion"], "gateways"),
    ("opencode-zen", "OpenCode Zen", "OpenCode Zen", "auto_awesome", "#6366F1", "OCZ", "https://opencode.ai/zen", True, "Free OpenCode endpoint — no API key needed", ["chat", "completion"], "gateways"),
    ("opencode-go", "OpenCode Go", "OpenCode Go", "auto_awesome", "#6366F1", "OCG", "https://opencode.ai/go", True, "Free OpenCode Go endpoint", ["chat", "completion"], "gateways"),
    ("dahl", "Dahl", "Dahl", "auto_awesome", "#6B7280", "DA", "https://inference.dahl.global", True, "Free — MiniMax M2.7, Kimi K2.6. Auto-generated token.", ["chat", "completion"], "gateways"),
    ("puter", "Puter AI", "Puter AI", "cloud_circle", "#6366F1", "PU", "https://puter.com", True, "500+ models — users pay via free Puter account", ["chat", "completion"], "gateways"),
    ("uncloseai", "UncloseAI", "UncloseAI", "auto_awesome", "#8B5CF6", "UN", "https://uncloseai.com", True, "Free forever — no signup, no credit card", ["chat", "completion"], "gateways"),
    ("hackclub", "Hackclub AI", "Hackclub AI", "auto_awesome", "#FF6B00", "HC", "https://ai.hackclub.com", True, "Free AI for Hack Club members — 30+ models", ["chat", "completion"], "gateways"),
    ("freetheai", "FreeTheAi", "FreeTheAi", "hub", "#22C55E", "FTA", "https://freetheai.xyz", True, "Free OpenAI-compatible gateway — sign up via Discord", ["chat", "completion"], "gateways"),
    ("g4f-groq", "g4f.space — Groq", "g4f.space — Groq", "bolt", "#F97316", "G4F", "https://g4f.space", True, "Free no-key reverse proxy to Groq — rate-limited 5 req/min", ["chat", "completion"], "gateways"),
    ("g4f-gemini", "g4f.space — Gemini", "g4f.space — Gemini", "bolt", "#F97316", "G4F", "https://g4f.space", True, "Free no-key reverse proxy to Gemini — rate-limited 5 req/min", ["chat", "completion"], "gateways"),
    ("g4f-pollinations", "g4f.space — Pollinations", "g4f.space — Pollinations", "bolt", "#F97316", "G4F", "https://g4f.space", True, "Free no-key reverse proxy to Pollinations — rate-limited 5 req/min", ["chat", "completion"], "gateways"),
    ("g4f-ollama", "g4f.space — Ollama", "g4f.space — Ollama", "bolt", "#F97316", "G4F", "https://g4f.space", True, "Free no-key hosted Ollama gateway — rate-limited 5 req/min", ["chat", "completion"], "gateways"),
    ("g4f-nvidia", "g4f.space — NVIDIA", "g4f.space — NVIDIA", "bolt", "#F97316", "G4F", "https://g4f.space", True, "Free no-key reverse proxy to NVIDIA NIM — rate-limited 5 req/min", ["chat", "completion"], "gateways"),
    ("vercel-ai-gateway", "Vercel AI Gateway", "Vercel AI Gateway", "route", "#111827", "VAI", "https://vercel.com/docs/ai-gateway", False, "Vercel AI Gateway — enterprise multi-model routing", ["chat", "completion"], "gateways"),
    ("llm7", "LLM7.io", "LLM7.io", "hub", "#6366F1", "LM", "https://llm7.io", True, "No signup required — 2 req/s, 20 RPM, 100 req/hr free", ["chat", "completion"], "gateways"),
    ("llamagate", "LlamaGate", "LlamaGate", "gate", "#16A34A", "LG", "https://llamagate.ai", False, "LlamaGate multi-model gateway", ["chat", "completion"], "gateways"),
    ("gitlawb", "Gitlawb Opengateway", "Gitlawb Opengateway (MiMo)", "hub", "#10B981", "GLB", "https://opengateway.gitlawb.com", False, "Free MiMo revoked — now pay-as-you-go credit gateway", ["chat", "completion"], "gateways"),
    ("gitlawb-gmi", "Gitlawb (GMI Cloud)", "Gitlawb Opengateway (GMI Cloud)", "hub", "#10B981", "GMI", "https://opengateway.gitlawb.com", False, "Free Nemotron promo ended — now pay-as-you-go credit only", ["chat", "completion"], "gateways"),
    ("nanogpt", "NanoGPT", "NanoGPT", "chat", "#4F46E5", "NG", "https://nano-gpt.com", False, "NanoGPT — pay-as-you-go LLM access", ["chat", "completion"], "gateways"),
    ("factory", "Factory", "Factory", "smart_toy", "#0F172A", "FA", "https://factory.ai", False, "Factory Droids — subscription coding agent gateway", ["chat", "completion", "code"], "gateways"),
    ("bluesminds", "BluesMinds", "BluesMinds", "psychology", "#3B82F6", "BM", "https://www.bluesminds.com", True, "Free daily pi credits — 200+ models", ["chat", "completion"], "gateways"),
    ("freemodel-dev", "FreeModel.dev", "FreeModel.dev", "auto_awesome", "#8B5CF6", "FM", "https://freemodel.dev", True, "$300 free credits on signup — no credit card", ["chat", "completion"], "gateways"),
    ("freeaiapikey", "FreeAIAPIKey", "FreeAIAPIKey", "vpn_key", "#F59E0B", "FK", "https://freeaiapikey.com", False, "Discounted API proxy for 40+ models", ["chat", "completion"], "gateways"),
    ("zenmux", "ZenMux", "ZenMux", "neurology", "#7C3AED", "ZM", "https://zenmux.ai", True, "Free tier — Gemini 3 Flash, DeepSeek V3.2, Grok 4.1 Fast", ["chat", "completion"], "gateways"),
    ("openadapter", "OpenAdapter", "OpenAdapter", "hub", "#10B981", "OD", "https://openadapter.dev", True, "Free tier — 15+ open-source models with daily quota", ["chat", "completion"], "gateways"),
    ("dit", "DIT.ai", "DIT.ai", "hub", "#0EA5E9", "DT", "https://dit.ai", False, "DIT.ai — dynamic per-request pricing router", ["chat", "completion"], "gateways"),
    ("tokenrouter", "TokenRouter", "TokenRouter", "hub", "#F59E0B", "TK", "https://tokenrouter.com", True, "Free tier — MiniMax 3 model included", ["chat", "completion"], "gateways"),
    ("sumopod", "SumoPod", "SumoPod", "router", "#2563EB", "SP", "https://ai.sumopod.com", False, "SumoPod — OpenAI-compatible multi-model router", ["chat", "completion"], "gateways"),
    ("x5lab", "X5Lab", "X5Lab", "router", "#7C3AED", "X5", "https://x5lab.dev", False, "X5Lab — OpenAI-compatible multi-model router", ["chat", "completion"], "gateways"),
    ("chenzk", "Chenzk API", "Chenzk API", "hub", "#10B981", "CZ", "https://chenzk.top", False, "Chenzk API gateway", ["chat", "completion"], "gateways"),
    ("kenari", "Kenari", "Kenari", "hub", "#B5362A", "KN", "https://kenari.id", False, "Kenari — OpenAI-compatible gateway", ["chat", "completion"], "gateways"),
    ("bai", "b.ai", "b.ai", "hub", "#6366F1", "BA", "https://b.ai", False, "b.ai — OpenAI-compatible LLM gateway", ["chat", "completion"], "gateways"),

    # ═══ enterprise-cloud ═══
    ("azure-ai", "Azure AI Foundry", "Azure AI Foundry", "cloud", "#2563EB", "AF", "https://learn.microsoft.com/azure/ai-foundry", False, "Azure AI Foundry — enterprise AI platform", ["chat", "completion", "embedding"], "enterprise-cloud"),
    ("watsonx", "IBM watsonx.ai", "IBM watsonx.ai Gateway", "hub", "#0F62FE", "WX", "https://www.ibm.com/products/watsonx-ai", False, "IBM watsonx.ai — enterprise AI gateway", ["chat", "completion"], "enterprise-cloud"),
    ("oci", "OCI Generative AI", "OCI Generative AI", "cloud", "#C74634", "OCI", "https://www.oracle.com/artificial-intelligence/generative-ai", False, "Oracle Cloud Infrastructure Generative AI", ["chat", "completion"], "enterprise-cloud"),
    ("sap", "SAP AI Hub", "SAP Generative AI Hub", "business", "#0FAAFF", "SAP", "https://help.sap.com/docs/sap-ai-core", False, "SAP Generative AI Hub — enterprise AI core", ["chat", "completion"], "enterprise-cloud"),
    ("modal", "Modal", "Modal", "cloud_queue", "#7C3AED", "MDL", "https://modal.com/docs", True, "$30/month free credits for new accounts", ["chat", "completion"], "enterprise-cloud"),
    ("vertex-partner", "Vertex AI Partners", "Vertex AI Partners", "cloud", "#34A853", "VP", "https://cloud.google.com/vertex-ai", False, "Vertex AI partner models (same auth as Vertex AI)", ["chat", "completion"], "enterprise-cloud"),
    ("ovhcloud", "OVHcloud AI", "OVHcloud AI", "cloud", "#2563EB", "OVH", "https://www.ovhcloud.com", False, "OVHcloud AI — European cloud AI", ["chat", "completion"], "enterprise-cloud"),
    ("heroku", "Heroku AI", "Heroku AI", "cloud_upload", "#7C3AED", "HK", "https://www.heroku.com", False, "Heroku AI — PaaS AI inference", ["chat", "completion"], "enterprise-cloud"),
    ("datarobot", "DataRobot", "DataRobot", "precision_manufacturing", "#6D28D9", "DR", "https://docs.datarobot.com", False, "DataRobot — enterprise AI platform", ["chat", "completion"], "enterprise-cloud"),
    ("clarifai", "Clarifai", "Clarifai", "hub", "#7C3AED", "CF", "https://docs.clarifai.com", False, "Clarifai — AI platform for image/video/text", ["chat", "completion", "image"], "enterprise-cloud"),

    # ═══ regional ═══
    ("glm", "GLM Coding", "GLM Coding", "code", "#2563EB", "GL", "https://z.ai/subscribe", False, "GLM Coding — Zhipu AI coding models", ["chat", "completion", "code"], "regional"),
    ("glm-cn", "GLM Coding (China)", "GLM Coding (China)", "code", "#DC2626", "GC", "https://open.bigmodel.cn", False, "GLM Coding — Zhipu AI China endpoint", ["chat", "completion", "code"], "regional"),
    ("glmt", "GLM Thinking", "GLM Thinking", "psychology", "#1D4ED8", "GT", "https://open.bigmodel.cn", False, "GLM Thinking — higher token budget, thinking enabled", ["chat", "completion"], "regional"),
    ("bailian-coding-plan", "Alibaba Coding Plan", "Alibaba Coding Plan", "code", "#FF6A00", "BCP", "https://www.alibabacloud.com/help/en/model-studio/coding-plan", False, "Alibaba Cloud Bailian Coding Plan", ["chat", "completion", "code"], "regional"),
    ("kimi-coding-apikey", "Kimi Code API Key", "Kimi Code API Key", "psychology", "#1E40AF", "KC", "https://www.kimi.com/code", False, "Kimi Code — API key auth for Kimi coding models", ["chat", "completion", "code"], "regional"),
    ("minimax-cn", "Minimax (China)", "Minimax (China)", "memory", "#DC2626", "MC", "https://www.minimaxi.com", False, "Minimax China endpoint", ["chat", "completion"], "regional"),
    ("zai", "Z.AI", "Z.AI", "psychology", "#2563EB", "ZA", "https://open.bigmodel.cn", False, "Z.AI — Zhipu AI API", ["chat", "completion"], "regional"),
    ("alibaba-cn", "Alibaba (China)", "Alibaba (China)", "cloud_queue", "#FF6600", "AL", "https://dashscope.console.aliyun.com", False, "Alibaba China — DashScope endpoint", ["chat", "completion"], "regional"),
    ("longcat", "LongCat AI", "LongCat AI", "auto_awesome", "#FF6B9D", "LC", "https://longcat.chat/platform/docs", True, "Free: one-time 10M-token grant after signup + KYC", ["chat", "completion"], "regional"),
    ("moonshot", "Moonshot AI", "Moonshot AI", "rocket_launch", "#1E40AF", "MS", "https://platform.moonshot.ai", False, "Moonshot AI — Kimi maker", ["chat", "completion"], "regional"),
    ("volcengine", "Volcengine", "Volcengine", "local_fire_department", "#DC2626", "VE", "https://www.volcengine.com", False, "Volcengine — ByteDance cloud AI", ["chat", "completion"], "regional"),
    ("xiaomi-mimo", "Xiaomi MiMo", "Xiaomi MiMo", "devices", "#EA580C", "MM", "https://mimo.mi.com", False, "Xiaomi MiMo models", ["chat", "completion"], "regional"),
    ("baidu", "Baidu (ERNIE)", "Baidu (ERNIE)", "auto_awesome", "#2932E1", "BD", "https://yiyan.baidu.com", True, "Free ERNIE Speed/Lite models — China's #2 LLM", ["chat", "completion"], "regional"),
    ("tencent", "Tencent Hunyuan", "Tencent Hunyuan", "auto_awesome", "#07C160", "TC", "https://hunyuan.tencent.com", True, "Free Hunyuan Lite models — WeChat ecosystem", ["chat", "completion"], "regional"),
    ("iflytek", "iFlytek Spark", "iFlytek Spark", "auto_awesome", "#0066FF", "IF", "https://xinghuo.xfyun.cn", True, "Spark Lite free (rate-limited) — Chinese real-name auth required", ["chat", "completion"], "regional"),
    ("baichuan", "Baichuan", "Baichuan", "auto_awesome", "#6366F1", "BC", "https://baichuan.com", True, "Free Baichuan models — popular Chinese LLM startup", ["chat", "completion"], "regional"),
    ("yi", "Yi (01.AI)", "Yi (01.AI)", "auto_awesome", "#10B981", "YI", "https://01.ai", False, "No free API tier (2026) — Yi-Light retired", ["chat", "completion"], "regional"),
    ("stepfun", "StepFun", "StepFun", "auto_awesome", "#8B5CF6", "SF", "https://stepfun.com", True, "Free Step-2 models — Chinese AI company", ["chat", "completion"], "regional"),
    ("coze", "Coze", "Coze", "smart_toy", "#3B82F6", "CZ", "https://coze.com", True, "Free ByteDance agent platform — bot building + LLM access", ["chat", "completion"], "regional"),
    ("360ai", "360 AI", "360 AI", "auto_awesome", "#00B96B", "360", "https://ai.360.cn", True, "Free 360 AI Brain models — major Chinese security company", ["chat", "completion"], "regional"),
    ("doubao", "Doubao", "Doubao", "auto_awesome", "#FE2C55", "DB", "https://doubao.com", True, "Free Doubao models — ByteDance's chatbot", ["chat", "completion"], "regional"),
    ("sensenova", "SenseNova", "SenseNova", "auto_awesome", "#0066FF", "SN", "https://platform.sensenova.cn", True, "Free SenseTime models — computer vision leader", ["chat", "completion"], "regional"),
    ("sparkdesk", "SparkDesk", "SparkDesk", "auto_awesome", "#0066FF", "SD", "https://xinghuo.xfyun.cn", True, "Spark Lite free — alias for iFlytek, personal use only", ["chat", "completion"], "regional"),
    ("hcnsec", "Huancheng Public API", "Huancheng Public API", "security", "#0EA5E9", "HC", "https://api.hcnsec.cn", True, "Free credits with daily check-ins", ["chat", "completion"], "regional"),
    ("agnes", "Agnes AI", "Agnes AI", "auto_awesome", "#10B981", "AG", "https://agnes-ai.com", True, "Permanently free API — no credit card required", ["chat", "completion"], "regional"),

    # ═══ specialty-media ═══
    ("kie", "KIE.AI", "KIE.AI", "hub", "#2563EB", "KIE", "https://kie.ai", False, "KIE.AI — image/video generation", ["image", "video"], "specialty-media"),
    ("freepik", "Freepik (Mystic)", "Freepik (Mystic)", "image", "#1B9E7F", "FP", "https://freepik.com", True, "One-time ~€5 API credit for new accounts", ["image"], "specialty-media"),
    ("jina-reader", "Jina Reader", "Jina Reader", "menu_book", "#0EA5E9", "JR", "https://jina.ai/reader", True, "Free tier: 1M fetches/month", ["webFetch"], "specialty-media"),
    ("tinyfish", "TinyFish Fetch", "TinyFish Fetch", "language", "#0891B2", "TF", "https://docs.tinyfish.ai/fetch-api", False, "Fetch API — up to 10 URLs per request", ["webFetch"], "specialty-media"),

    # ═══ noauth ═══
    ("opencode", "OpenCode Free", "OpenCode Free", "terminal", "#E87040", "OC", "https://opencode.ai", True, "No API key required — public OpenCode endpoint with Kimi, GLM, Qwen, MiMo, MiniMax", ["chat", "completion"], "noauth"),
    ("duckduckgo-web", "DuckDuckGo AI Chat", "DuckDuckGo AI Chat", "auto_awesome", "#DE5833", "DDG", "https://duckduckgo.com/duckchat", True, "Free — anonymous access to multiple AI models via DuckDuckGo", ["chat", "completion"], "noauth"),
    ("felo-web", "Felo", "Felo", "travel_explore", "#5B7FFF", "FL", "https://felo.ai", True, "Free — anonymous access to Felo's chat/search-agent aggregator", ["chat", "completion"], "noauth"),
    ("theoldllm", "The Old LLM (Free)", "The Old LLM (Free)", "auto_awesome", "#8B5CF6", "TL", "https://theoldllm.vercel.app", True, "Free — GPT-5.4, Claude 4.6 Opus/Sonnet/Haiku, no API key", ["chat", "completion"], "noauth"),
    ("chipotle", "Chipotle Pepper AI", "Chipotle Pepper AI (Free)", "restaurant", "#C41230", "🌶", "https://amelia.chipotle.com", True, "Free — Chipotle's Pepper AI, anonymous sessions, rate-limited", ["chat", "completion"], "noauth"),
    ("veoaifree-web", "Veo AI Free", "Veo AI Free", "videocam", "#8B5CF6", "VF", "https://veoaifree.com", True, "Free video generation — VEO 3.1, Seedance. 6 req/hour.", ["video"], "noauth"),
    ("mimocode", "MiMoCode (Free)", "MiMoCode (Free)", "devices", "#FF6B35", "MC", "https://mimo.mi.com", True, "Free — Xiaomi MiMo models via bootstrap JWT auth", ["chat", "completion"], "noauth"),
    ("auggie", "Augment (Auggie CLI)", "Augment (Auggie CLI)", "terminal", "#7C3AED", "AU", "https://augmentcode.com", False, "Local passthrough — runs Augment CLI on this machine", ["chat", "completion"], "noauth"),

    # ═══ oauth ═══
    ("xai-oauth", "xAI OAuth", "xAI OAuth (Grok)", "auto_awesome", "#1DA1F2", "XA", "https://x.ai", False, "xAI OAuth — sign in to use Grok models", ["chat", "completion"], "oauth"),
    ("grok-cli", "Grok Build", "Grok Build", "bolt", "#000000", "GB", "", False, "Grok Build — paste JWT from CLI", ["chat", "completion"], "oauth"),
    ("qoder", "Qoder", "Qoder", "water_drop", "#6366F1", "QD", "", True, "Qoder — free coding agent", ["chat", "completion", "code"], "oauth"),
    ("qwen", "Qwen Code", "Qwen Code", "psychology", "#10B981", "QW", "", False, "Deprecated — Qwen OAuth free tier discontinued 2026-04", ["chat", "completion"], "oauth"),
    ("agy", "Antigravity CLI", "Antigravity CLI", "terminal", "#F59E0B", "AGY", "https://antigravity.google", True, "Antigravity CLI — sign in with Google", ["chat", "completion"], "oauth"),
    ("kiro", "Kiro AI", "Kiro AI", "psychology_alt", "#FF6B35", "KR", "", True, "Free tier: 50 credits/month — ToS prohibits third-party use", ["chat", "completion"], "oauth"),
    ("amazon-q", "Amazon Q", "Amazon Q", "cloud", "#FF9900", "AQ", "https://aws.amazon.com/q/developer/", True, "Amazon Q Developer — free tier", ["chat", "completion", "code"], "oauth"),
    ("claude", "Claude Code", "Claude Code", "smart_toy", "#D97757", "CC", "", False, "Claude Code — OAuth subscription", ["chat", "completion", "code"], "oauth"),
    ("antigravity", "Antigravity", "Antigravity", "rocket_launch", "#F59E0B", "AG", "", False, "Antigravity — Google AI agent", ["chat", "completion"], "oauth"),
    ("codex", "OpenAI Codex", "OpenAI Codex", "code", "#3B82F6", "CX", "", False, "OpenAI Codex — OAuth subscription", ["chat", "completion", "code"], "oauth"),
    ("github", "GitHub Copilot", "GitHub Copilot", "code", "#333333", "GH", "", False, "GitHub Copilot — OAuth", ["chat", "completion", "code"], "oauth"),
    ("gitlab-duo", "GitLab Duo", "GitLab Duo", "hub", "#FC6D26", "GL", "https://docs.gitlab.com/user/duo_agent_platform/code_suggestions/", False, "GitLab Duo — OAuth application", ["chat", "completion", "code"], "oauth"),
    ("cursor", "Cursor IDE", "Cursor IDE", "edit_note", "#00D4AA", "CU", "", False, "Cursor IDE — OAuth subscription", ["chat", "completion", "code"], "oauth"),
    ("zed", "Zed IDE", "Zed IDE", "code", "#084CCF", "ZD", "https://zed.dev", False, "Zed IDE — import LLM provider credentials from OS keychain", ["chat", "completion"], "oauth"),
    ("zed-hosted", "Zed Hosted Models", "Zed Hosted Models", "code_blocks", "#101010", "ZH", "https://zed.dev", False, "Zed Hosted — chat through Zed's hosted model aggregator", ["chat", "completion"], "oauth"),
    ("trae", "Trae", "Trae", "edit_square", "#FF7849", "TR", "https://trae.ai", False, "Trae — ByteDance AI-native IDE", ["chat", "completion"], "oauth"),
    ("kimi-coding", "Kimi Code CLI", "Kimi Code CLI", "psychology", "#1E40AF", "KC", "", False, "Kimi Code CLI — OAuth flow", ["chat", "completion", "code"], "oauth"),
    ("kilocode", "Kilo Code", "Kilo Code", "code", "#FF6B35", "KC", "", False, "Kilo Code — free models without signup", ["chat", "completion", "code"], "oauth"),
    ("cline", "Cline", "Cline", "smart_toy", "#5B9BD5", "CL", "", False, "Cline — OAuth subscription", ["chat", "completion", "code"], "oauth"),
    ("clinepass", "ClinePass", "ClinePass", "smart_toy", "#9D4EDD", "CP", "https://cline.bot/clinepass", False, "ClinePass — $9.99/mo bundling 10 open coding models", ["chat", "completion", "code"], "oauth"),
    ("windsurf", "Windsurf", "Windsurf (Devin CLI)", "air", "#00C5A0", "WS", "https://windsurf.com", False, "Windsurf — provide auth token from IDE", ["chat", "completion", "code"], "oauth"),
    ("devin-cli", "Devin CLI", "Devin CLI (Official)", "terminal", "#6366F1", "DV", "https://cli.devin.ai", False, "Devin CLI — run `devin auth login` to authenticate", ["chat", "completion", "code"], "oauth"),
    ("codebuddy-cn", "CodeBuddy CN", "CodeBuddy CN", "smart_toy", "#006EFF", "CB", "https://copilot.tencent.com", False, "Tencent CodeBuddy CN — GLM / Kimi / MiniMax / DeepSeek / Hunyuan", ["chat", "completion", "code"], "oauth"),

    # ═══ web-cookie ═══
    ("chatgpt-web", "ChatGPT Web", "ChatGPT Web (Plus/Pro)", "auto_awesome", "#10A37F", "CG", "https://chatgpt.com", False, "Paste session cookie from chatgpt.com", ["chat", "completion"], "web-cookie"),
    ("grok-web", "Grok Web", "Grok Web (Subscription)", "auto_awesome", "#1DA1F2", "GW", "https://grok.com", False, "Paste grok.com cookie line from DevTools", ["chat", "completion"], "web-cookie"),
    ("gemini-web", "Gemini Web", "Gemini Web (Free)", "auto_awesome", "#4285F4", "GWeb", "https://gemini.google.com", True, "Free — paste __Secure-1PSID cookie from gemini.google.com", ["chat", "completion"], "web-cookie"),
    ("perplexity-web", "Perplexity Web", "Perplexity Web (Pro/Max)", "search", "#20808D", "PW", "https://www.perplexity.ai", False, "Paste session cookie from perplexity.ai", ["chat", "completion", "search"], "web-cookie"),
    ("blackbox-web", "Blackbox Web", "Blackbox Web (Subscription)", "view_in_ar", "#1A1A2E", "BW", "https://app.blackbox.ai", False, "Paste session token from app.blackbox.ai", ["chat", "completion"], "web-cookie"),
    ("muse-spark-web", "Muse Spark Web", "Muse Spark Web (Meta AI)", "auto_awesome", "#0866FF", "MS", "https://www.meta.ai", True, "Free with login — Meta AI with Llama models", ["chat", "completion"], "web-cookie"),
    ("claude-web", "Claude Web", "Claude Web", "auto_awesome", "#D97757", "CW", "https://claude.ai", False, "Paste session cookie from claude.ai", ["chat", "completion"], "web-cookie"),
    ("deepseek-web", "DeepSeek Web", "DeepSeek Web", "auto_awesome", "#4D6BFE", "DS", "https://chat.deepseek.com", False, "Paste userToken from chat.deepseek.com Local Storage", ["chat", "completion"], "web-cookie"),
    ("copilot-web", "Microsoft Copilot Web", "Microsoft Copilot Web", "auto_awesome", "#0078D4", "CP", "https://copilot.microsoft.com", False, "Paste access_token from copilot.microsoft.com", ["chat", "completion"], "web-cookie"),
    ("copilot-m365-web", "Microsoft 365 Copilot", "Microsoft 365 Copilot (BizChat)", "business_center", "#0078D4", "M365", "https://m365.cloud.microsoft/chat", False, "Paste WebSocket Chathub access_token from DevTools", ["chat", "completion"], "web-cookie"),
    ("microsoft-designer-web", "Microsoft Designer", "Microsoft Designer (Image Generation)", "auto_awesome", "#0078D4", "MSD", "https://designer.microsoft.com", False, "Paste Bearer token from Designer DevTools", ["image"], "web-cookie"),
    ("t3-web", "t3.chat", "t3.chat (Pro/Free)", "auto_awesome", "#7C3AED", "T3", "https://t3.chat", True, "Free tier limited access — Pro ($8/mo) unlocks 50+ models", ["chat", "completion"], "web-cookie"),
    ("inner-ai", "Inner.ai", "Inner.ai (Subscription)", "auto_awesome", "#1A56DB", "IA", "https://app.innerai.com", False, "Paste token cookie + email from .innerai.com", ["chat", "completion"], "web-cookie"),
    ("adapta-web", "Adapta.org", "Adapta.org (Adapta One Web)", "auto_awesome", "#6E3AD3", "AW", "https://agent.adapta.one", False, "Paste __client cookie from .clerk.agent.adapta.one", ["chat", "completion"], "web-cookie"),
    ("lmarena", "Arena (Free)", "Arena (Free)", "auto_awesome", "#FF6B6B", "AR", "https://arena.ai", True, "Free model comparison platform (formerly LMArena) at arena.ai", ["chat", "completion"], "web-cookie"),
    ("yuanbao-web", "Tencent Yuanbao", "Tencent Yuanbao (Free)", "auto_awesome", "#0052D9", "YB", "https://yuanbao.tencent.com", True, "Free — DeepSeek V3/R1 and Hunyuan via web session", ["chat", "completion"], "web-cookie"),
    ("huggingchat", "HuggingChat", "HuggingChat (Free)", "auto_awesome", "#FFD21E", "HC", "https://huggingface.co/chat", True, "Free LLM chat — no subscription required", ["chat", "completion"], "web-cookie"),
    ("poe-web", "Poe Web", "Poe Web (Subscription)", "auto_awesome", "#6C3AED", "PW", "https://poe.com", False, "Paste p-b cookie from poe.com", ["chat", "completion"], "web-cookie"),
    ("venice-web", "Venice Web", "Venice Web (Privacy)", "auto_awesome", "#22C55E", "VW", "https://venice.ai", False, "Paste session cookie from venice.ai", ["chat", "completion"], "web-cookie"),
    ("v0-vercel-web", "v0 Vercel Web", "v0 Vercel Web (Code Gen)", "auto_awesome", "#000000", "V0", "https://v0.dev", False, "Paste session cookie from v0.dev", ["code", "chat"], "web-cookie"),
    ("kimi-web", "Kimi Web", "Kimi Web", "auto_awesome", "#2563EB", "KW", "https://www.kimi.com", False, "Paste access_token from www.kimi.com Local Storage", ["chat", "completion"], "web-cookie"),
    ("doubao-web", "Dola Web", "Dola Web (ByteDance)", "auto_awesome", "#3B82F6", "DA", "https://www.dola.com", False, "Paste full Cookie header from www.dola.com", ["chat", "completion"], "web-cookie"),
    ("qwen-web", "Qwen Web", "Qwen Web (Free)", "auto_awesome", "#10B981", "QW", "https://chat.qwen.ai", True, "Free — Qwen models via chat.qwen.ai with login token", ["chat", "completion"], "web-cookie"),
    ("gemini-business", "Gemini Business", "Gemini Business (Enterprise)", "business_center", "#4285F4", "GB", "https://business.gemini.google", True, "Free for Google Workspace enterprise accounts", ["chat", "completion"], "web-cookie"),
    ("zenmux-free", "ZenMux Free", "ZenMux Free (Web)", "bolt", "#667eea", "ZF", "https://zenmux.ai", True, "Free tier (5 Flows/5h) — DeepSeek V3.2, GLM 4.7 Flash Free", ["chat", "completion"], "web-cookie"),
    ("zai-web", "Z.ai Web", "Z.ai Web (Free)", "auto_awesome", "#2563EB", "ZW", "https://chat.z.ai", True, "Free — GLM chat models via chat.z.ai", ["chat", "completion"], "web-cookie"),
    ("notion-web", "Notion AI Web", "Notion AI Web (Unofficial)", "auto_awesome", "#000000", "NW", "https://www.notion.so", False, "Paste token_v2 cookie from app.notion.com", ["chat", "completion"], "web-cookie"),

    # ═══ local ═══
    ("vllm", "vLLM", "vLLM", "memory", "#0F766E", "VL", "https://github.com/vllm-project/vllm", True, "Free — open-source local LLM inference server", ["chat", "completion"], "local"),
    ("lemonade", "Lemonade Server", "Lemonade Server", "bolt", "#F59E0B", "LM", "https://lemonade-server.ai", True, "Free — local LLM server", ["chat", "completion"], "local"),
    ("llama-cpp", "llama.cpp", "llama.cpp", "memory", "#795548", "LC", "https://github.com/ggml-org/llama.cpp", True, "Free — open-source C++ LLM inference", ["chat", "completion"], "local"),
    ("triton", "NVIDIA Triton", "NVIDIA Triton", "developer_board", "#76B900", "TR", "https://developer.nvidia.com/triton-inference-server", True, "Free — NVIDIA inference server", ["chat", "completion"], "local"),
    ("docker-model-runner", "Docker Model Runner", "Docker Model Runner", "inventory_2", "#2496ED", "DM", "https://docs.docker.com/ai/model-runner/", True, "Free — Docker desktop AI model runner", ["chat", "completion"], "local"),
    ("xinference", "XInference", "XInference", "hub", "#DC2626", "XI", "https://inference.readthedocs.io", True, "Free — distributed inference framework", ["chat", "completion"], "local"),
    ("oobabooga", "oobabooga", "oobabooga", "dns", "#8B5CF6", "OO", "https://github.com/oobabooga/text-generation-webui", True, "Free — text-generation-webui local server", ["chat", "completion"], "local"),
    ("sdwebui", "SD WebUI", "SD WebUI", "brush", "#FF7043", "SD", "https://github.com/AUTOMATIC1111/stable-diffusion-webui", True, "Free — Stable Diffusion WebUI", ["image"], "local"),
    ("comfyui", "ComfyUI", "ComfyUI", "account_tree", "#4CAF50", "CF", "https://github.com/comfyanonymous/ComfyUI", True, "Free — node-based Stable Diffusion UI", ["image"], "local"),

    # ═══ search ═══
    ("perplexity-search", "Perplexity Search", "Perplexity Search", "search", "#20808D", "PS", "https://docs.perplexity.ai/guides/search-quickstart", False, "Perplexity Search API — same key as Perplexity", ["search"], "search"),
    ("serper-search", "Serper Search", "Serper Search", "search", "#4285F4", "SP", "https://serper.dev", True, "Serper Search API — Google search results", ["search"], "search"),
    ("exa-search", "Exa Search", "Exa Search", "neurology", "#1E40AF", "EX", "https://exa.ai", True, "Exa Search API — neural search engine", ["search", "webFetch"], "search"),
    ("tavily-search", "Tavily Search", "Tavily Search", "manage_search", "#5B4FDB", "TV", "https://tavily.com", True, "Tavily Search API — AI search", ["search", "webFetch"], "search"),
    ("google-pse-search", "Google Programmable Search", "Google Programmable Search", "travel_explore", "#4285F4", "GP", "https://developers.google.com/custom-search/v1/overview", False, "Requires Google API key + PSE ID (cx)", ["search"], "search"),
    ("linkup-search", "Linkup Search", "Linkup Search", "public", "#0F766E", "LU", "https://docs.linkup.so", False, "Linkup Search API", ["search"], "search"),
    ("searchapi-search", "SearchAPI", "SearchAPI", "manage_search", "#2563EB", "SA", "https://www.searchapi.io/docs/google", False, "SearchAPI — Google search results API", ["search"], "search"),
    ("youcom-search", "You.com Search", "You.com Search", "travel_explore", "#2563EB", "YOU", "https://you.com/business/api/", False, "You.com Search API", ["search"], "search"),
    ("searxng-search", "SearXNG Search", "SearXNG Search", "search", "#1A237E", "SX", "https://docs.searxng.org", True, "SearXNG — open-source metasearch engine (API key optional)", ["search"], "search"),
    ("ollama-search", "Ollama Search", "Ollama Search", "search", "#58A6FF", "OS", "https://ollama.com/settings/keys", False, "Ollama Search — same API key as Ollama Cloud", ["search"], "search"),

    # ═══ audio ═══
    ("inworld", "Inworld", "Inworld", "voice_chat", "#7B2EF2", "IW", "https://inworld.ai", False, "Inworld — AI character engine", ["audio", "tts"], "audio"),
    ("aws-polly", "AWS Polly", "AWS Polly", "record_voice_over", "#FF9900", "PL", "https://aws.amazon.com/polly/", False, "AWS Polly — Amazon TTS service", ["tts", "audio"], "audio"),
    ("gladia", "Gladia", "Gladia", "record_voice_over", "#6425FE", "GL", "https://gladia.io", False, "Gladia — speech-to-text API", ["stt", "audio"], "audio"),
    ("rev-ai", "Rev AI", "Rev AI", "record_voice_over", "#FF5C35", "RV", "https://www.rev.ai", False, "Rev AI — speech-to-text API", ["stt", "audio"], "audio"),
    ("speechmatics", "Speechmatics", "Speechmatics", "record_voice_over", "#0A2540", "SM", "https://www.speechmatics.com", True, "Free tier — 8 hours/month, batch mode only", ["stt", "audio"], "audio"),

    # ═══ upstream-proxy ═══
    ("cliproxyapi", "CLIProxyAPI", "CLIProxyAPI", "proxy", "#6366F1", "CPA", "https://github.com/router-for-me/CLIProxyAPI", True, "Free — open-source local proxy router", ["chat", "completion"], "upstream-proxy"),
    ("9router", "9router", "9router", "router", "#0EA5E9", "9R", "https://www.npmjs.com/package/9router", True, "Free — embedded npm proxy router", ["chat", "completion"], "upstream-proxy"),

    # ═══ cloud-agent ═══
    ("jules", "Google Jules", "Google Jules", "engineering", "#4285F4", "JL", "https://jules.google", False, "Google Jules — cloud coding agent", ["chat", "completion", "code"], "cloud-agent"),
    ("devin", "Devin", "Devin", "smart_toy", "#111827", "DV", "https://devin.ai", False, "Devin — cloud AI software engineer", ["chat", "completion", "code"], "cloud-agent"),
    ("codex-cloud", "Codex Cloud", "Codex Cloud", "cloud", "#10A37F", "CC", "https://openai.com/codex", False, "OpenAI Codex Cloud — cloud coding tasks", ["chat", "completion", "code"], "cloud-agent"),

    # ═══ system ═══
    ("auto", "Auto (Zero-Config)", "Auto (Zero-Config)", "auto_awesome", "#6366F1", "Auto", "", True, "Zero-config auto-routing across all connected providers", ["chat", "completion"], "system"),
]


def make_entry(pid, alias, name, icon, color, textIcon, website, hasFree, freeNote, serviceKinds, category):
    """Generate a Python dict entry string for a provider."""
    lines = []
    lines.append(f'    "{pid}": {{')
    lines.append(f'        "id": "{pid}",')
    lines.append(f'        "alias": "{alias}",')
    lines.append(f'        "name": "{name}",')
    lines.append(f'        "icon": "{icon}",')
    lines.append(f'        "color": "{color}",')
    lines.append(f'        "textIcon": "{textIcon}",')
    lines.append(f'        "website": "{website}",')
    lines.append(f'        "hasFree": {repr(hasFree)},')
    # Escape quotes in freeNote
    escapedNote = freeNote.replace('"', '\\"')
    lines.append(f'        "freeNote": "{escapedNote}",')
    lines.append(f'        "serviceKinds": {repr(serviceKinds)},')
    lines.append(f'        "category": "{category}",')
    lines.append(f'    }},')
    return '\n'.join(lines)


def build_new_entries():
    """Build all new provider entry strings."""
    sections = {
        "inference-hosts": "#  EK ÇIKARIM SAĞLAYICILARI  (Inference Hosts)",
        "gateways": "#  EK GEÇİT SAĞLAYICILARI  (Gateways)",
        "enterprise-cloud": "#  EK KURUMSAL SAĞLAYICILARI  (Enterprise Cloud)",
        "regional": "#  EK BÖLGESEL SAĞLAYICILAR  (Regional)",
        "specialty-media": "#  EK ÖZEL MEDYA SAĞLAYICILARI  (Specialty Media)",
        "noauth": "#  ANONİM SAĞLAYICILAR  (No Auth)",
        "oauth": "#  OAUTH SAĞLAYICILAR  (OAuth)",
        "web-cookie": "#  WEB ÇEREZ SAĞLAYICILARI  (Web Cookie)",
        "local": "#  EK YEREL SAĞLAYICILAR  (Local / Self-hosted)",
        "search": "#  ARAMA SAĞLAYICILARI  (Search)",
        "audio": "#  EK SES SAĞLAYICILARI  (Audio)",
        "upstream-proxy": "#  YUKARI AKIŞ VEKİL SAĞLAYICILARI  (Upstream Proxy)",
        "cloud-agent": "#  BULUT AJAN SAĞLAYICILARI  (Cloud Agent)",
        "system": "#  SİSTEM SAĞLAYICILARI  (System)",
    }
    
    # Group providers by category
    by_cat = {}
    for entry in NEW_PROVIDERS:
        cat = entry[-1]  # category is last element
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(entry)
    
    result_parts = []
    for cat, header in sections.items():
        if cat not in by_cat:
            continue
        entries = by_cat[cat]
        result_parts.append(f'    # {"═" * 65}')
        result_parts.append(f'    {header}')
        result_parts.append(f'    # {"═" * 65}')
        for e in entries:
            result_parts.append(make_entry(*e))
    
    return '\n'.join(result_parts)


def main():
    # Read existing file
    with open('/opt/data/kopru/kopru/provider_catalog.py', 'r') as f:
        content = f.read()
    
    # Find the closing of the PROVIDER_CATALOG dict and the helper functions
    # The dict ends with "}" on its own line before the helper functions
    # Find the line with the closing brace of the dict (the one before "# ── Helper Functions")
    marker = "# ── Helper Functions"
    idx = content.find(marker)
    if idx == -1:
        print("ERROR: Could not find helper functions marker")
        sys.exit(1)
    
    # Find the last entry before the closing brace + blank line
    # We need to insert new entries before the closing "}" of PROVIDER_CATALOG
    # The pattern is: last entry's "}," then blank line then "}" then blank line then "# ── Helper Functions"
    
    # Find the closing "}" of the dict
    dict_close_pattern = re.compile(r'\n\}\n\n# ── Helper Functions', re.DOTALL)
    match = dict_close_pattern.search(content)
    if not match:
        print("ERROR: Could not find dict closing pattern")
        sys.exit(1)
    
    # Build new entries
    new_entries = build_new_entries()
    
    # Insert before the closing "}"
    insert_point = match.start()
    new_content = content[:insert_point] + '\n' + new_entries + '\n' + content[insert_point:]
    
    # Verify syntax
    try:
        compile(new_content, 'provider_catalog.py', 'exec')
        print("✅ Syntax check passed")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        sys.exit(1)
    
    # Write the file
    with open('/opt/data/kopru/kopru/provider_catalog.py', 'w') as f:
        f.write(new_content)
    
    # Count providers
    count = len(EXISTING_IDS) + len(NEW_PROVIDERS)
    print(f"✅ Written provider_catalog.py")
    print(f"   Existing providers: {len(EXISTING_IDS)}")
    print(f"   New providers: {len(NEW_PROVIDERS)}")
    print(f"   Total providers: {count}")
    
    # Show category breakdown
    by_cat = {}
    for e in NEW_PROVIDERS:
        cat = e[-1]
        by_cat[cat] = by_cat.get(cat, 0) + 1
    print(f"\n   New providers by category:")
    for cat, cnt in sorted(by_cat.items()):
        print(f"     {cat}: {cnt}")


if __name__ == "__main__":
    main()
