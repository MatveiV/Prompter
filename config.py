import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]

# API keys & base URLs for each provider
PROVIDERS = {
    "zai": {
        "name": "Z.AI",
        "api_key": os.environ.get("ZAI_API_KEY", ""),
        "base_url": "https://api.z.ai/api/paas/v4/",
        "models": [
            # price_in / price_out: ₽ per 1K tokens (GenAPI pricing page)
            {"id": "glm-4.7-flash", "label": "GLM-4.7-Flash (free)", "free": True,  "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 4096, "price_in": 0.0,   "price_out": 0.0},
            {"id": "glm-4.5-flash", "label": "GLM-4.5-Flash (free)", "free": True,  "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 4096, "price_in": 0.0,   "price_out": 0.0},
            {"id": "glm-4.7",       "label": "GLM-4.7",              "free": False, "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 8192, "price_in": 0.15,  "price_out": 0.55},
            {"id": "glm-4.5",       "label": "GLM-4.5",              "free": False, "context": "128K", "temp_range": (0.0, 1.0), "max_tokens_limit": 8192, "price_in": 0.15,  "price_out": 0.55},
            {"id": "glm-5",         "label": "GLM-5",                "free": False, "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 8192, "price_in": 0.25,  "price_out": 0.8},
        ],
    },
    "proxy": {
        "name": "ProxyAPI",
        "api_key": os.environ.get("PROXY_API_KEY", ""),
        "base_url": "https://api.proxyapi.ru/openai/v1",
        "models": [
            # ProxyAPI prices (₽ per 1M tokens → divide by 1000 for per-1K)
            {"id": "gpt-4.1-nano",  "label": "GPT-4.1 Nano",  "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768, "price_in": 0.026,  "price_out": 0.104},
            {"id": "gpt-4.1-mini",  "label": "GPT-4.1 Mini",  "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768, "price_in": 0.104,  "price_out": 0.413},
            {"id": "gpt-4.1",       "label": "GPT-4.1",        "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768, "price_in": 0.516,  "price_out": 2.062},
            {"id": "gpt-4o-mini",   "label": "GPT-4o Mini",    "free": False, "context": "128K", "temp_range": (0.0, 2.0), "max_tokens_limit": 16384, "price_in": 0.039,  "price_out": 0.155},
            {"id": "gpt-4o",        "label": "GPT-4o",         "free": False, "context": "128K", "temp_range": (0.0, 2.0), "max_tokens_limit": 16384, "price_in": 0.645,  "price_out": 2.577},
            {"id": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo",  "free": False, "context": "16K",  "temp_range": (0.0, 2.0), "max_tokens_limit": 4096,  "price_in": 0.129,  "price_out": 0.387},
        ],
    },
    "gen": {
        "name": "GenAPI",
        "api_key": os.environ.get("GEN_API_KEY", ""),
        "base_url": "https://proxy.gen-api.ru/v1",
        "models": [
            # GenAPI slugs use dashes instead of dots — verified on gen-api.ru/model/*
            {"id": "gpt-4-1-mini",                    "label": "GPT-4.1 Mini",       "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768, "price_in": 0.01,   "price_out": 0.04},
            {"id": "gpt-4-1",                         "label": "GPT-4.1",            "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768, "price_in": 0.4,    "price_out": 1.6},
            {"id": "gpt-4o",                          "label": "GPT-4o",             "free": False, "context": "128K", "temp_range": (0.0, 2.0), "max_tokens_limit": 16384, "price_in": 0.5,    "price_out": 2.0},
            {"id": "claude-sonnet-4-5",               "label": "Claude Sonnet 4.5",  "free": False, "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 8192,  "price_in": 0.8,    "price_out": 3.0},
            {"id": "gemini-2-5-flash",                "label": "Gemini 2.5 Flash",   "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 8192,  "price_in": 0.06,   "price_out": 0.5},
            {"id": "deepseek-chat",                   "label": "DeepSeek Chat",      "free": False, "context": "64K",  "temp_range": (0.0, 2.0), "max_tokens_limit": 8192,  "price_in": 0.07,   "price_out": 0.105},
            {"id": "deepseek-r1",                     "label": "DeepSeek R1",        "free": False, "context": "64K",  "temp_range": (0.0, 2.0), "max_tokens_limit": 16000, "price_in": 0.3,    "price_out": 1.5},
        ],
    },
}

# Default params per new session
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 256
MAX_CONTEXT_MESSAGES = 20  # keep last N messages per user
