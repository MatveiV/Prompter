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
            {"id": "glm-4.7-flash", "label": "GLM-4.7-Flash (free)", "free": True,  "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 4096},
            {"id": "glm-4.5-flash", "label": "GLM-4.5-Flash (free)", "free": True,  "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 4096},
            {"id": "glm-4.7",       "label": "GLM-4.7",              "free": False, "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 8192},
            {"id": "glm-4.5",       "label": "GLM-4.5",              "free": False, "context": "128K", "temp_range": (0.0, 1.0), "max_tokens_limit": 8192},
            {"id": "glm-5",         "label": "GLM-5",                "free": False, "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 8192},
        ],
    },
    "proxy": {
        "name": "ProxyAPI",
        "api_key": os.environ.get("PROXY_API_KEY", ""),
        "base_url": "https://api.proxyapi.ru/openai/v1",
        "models": [
            {"id": "gpt-4.1-nano",  "label": "GPT-4.1 Nano",  "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768},
            {"id": "gpt-4.1-mini",  "label": "GPT-4.1 Mini",  "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768},
            {"id": "gpt-4.1",       "label": "GPT-4.1",        "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768},
            {"id": "gpt-4o-mini",   "label": "GPT-4o Mini",    "free": False, "context": "128K", "temp_range": (0.0, 2.0), "max_tokens_limit": 16384},
            {"id": "gpt-4o",        "label": "GPT-4o",         "free": False, "context": "128K", "temp_range": (0.0, 2.0), "max_tokens_limit": 16384},
            {"id": "gpt-3.5-turbo", "label": "GPT-3.5 Turbo",  "free": False, "context": "16K",  "temp_range": (0.0, 2.0), "max_tokens_limit": 4096},
        ],
    },
    "gen": {
        "name": "GenAPI",
        "api_key": os.environ.get("GEN_API_KEY", ""),
        "base_url": "https://proxy.gen-api.ru/v1",
        "models": [
            {"id": "gpt-4.1-mini",       "label": "GPT-4.1 Mini",       "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 32768},
            {"id": "gpt-4o",             "label": "GPT-4o",              "free": False, "context": "128K", "temp_range": (0.0, 2.0), "max_tokens_limit": 16384},
            {"id": "claude-sonnet-4-5",  "label": "Claude Sonnet 4.5",   "free": False, "context": "200K", "temp_range": (0.0, 1.0), "max_tokens_limit": 8192},
            {"id": "gemini-2.5-flash",   "label": "Gemini 2.5 Flash",    "free": False, "context": "1M",   "temp_range": (0.0, 2.0), "max_tokens_limit": 8192},
            {"id": "deepseek-chat",      "label": "DeepSeek Chat",       "free": False, "context": "64K",  "temp_range": (0.0, 2.0), "max_tokens_limit": 8192},
            {"id": "deepseek-reasoner",  "label": "DeepSeek R1",         "free": False, "context": "64K",  "temp_range": (0.0, 2.0), "max_tokens_limit": 8192},
        ],
    },
}

# Default params per new session
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024
MAX_CONTEXT_MESSAGES = 20  # keep last N messages per user
