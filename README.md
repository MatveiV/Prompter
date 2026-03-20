# 3API — Multi-provider AI CLI + Telegram Bot

Три CLI-скрипта и Telegram-бот для тестирования разных AI-провайдеров: **Z.AI**, **ProxyAPI**, **GenAPI**.

## Структура

```
.
├── bot.py              # Telegram-бот (aiogram)
├── config.py           # Токены, провайдеры, модели
├── context_manager.py  # In-memory контекст диалога
├── openai_client.py    # Единый OpenAI-совместимый клиент
├── zai_direct.py       # CLI — Z.AI
├── proxy_api.py        # CLI — ProxyAPI
├── gen_api.py          # CLI — GenAPI
├── .env                # Секреты (не коммитить)
├── .env.example        # Шаблон .env
├── .gitignore
└── requirements.txt
```

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt

cp .env.example .env
# заполни .env своими ключами
```

## .env

```env
BOT_TOKEN=your_telegram_bot_token

ZAI_API_KEY=...        # https://api.z.ai/api/paas/v4/
PROXY_API_KEY=...      # https://api.proxyapi.ru/openai/v1
GEN_API_KEY=...        # https://proxy.gen-api.ru/v1
```

## CLI-скрипты

```bash
python zai_direct.py   # Z.AI (GLM-модели, есть бесплатные)
python proxy_api.py    # ProxyAPI → OpenAI GPT
python gen_api.py      # GenAPI → GPT / Claude / Gemini / DeepSeek
```

Каждый скрипт интерактивно предлагает выбрать модель, температуру, max_tokens, system message.

## Telegram-бот

```bash
python bot.py
```

### Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие + мастер настройки |
| `/setup` | Выбрать провайдера, модель, параметры |
| `/info` | Текущие настройки сессии |
| `/clear` | Очистить историю диалога |
| `/report` | Таблица прогонов моделей |
| `/help` | Справка |

Написать `очистить контекст` — тоже сбрасывает историю.

### Логика

- Каждый пользователь имеет свой контекст (последние 20 сообщений в памяти).
- После каждого ответа контекст обновляется.
- `/report` показывает таблицу: провайдер, модель, температура, max_tokens, № прогона, токены (in/out/total), finish_reason.

## Провайдеры и модели

### Z.AI (`zai_direct.py`, бот)
| Модель | Контекст | Бесплатно |
|--------|----------|-----------|
| GLM-4.7-Flash | 200K | ✅ |
| GLM-4.5-Flash | 200K | ✅ |
| GLM-4.7 | 200K | — |
| GLM-4.5 | 128K | — |
| GLM-5 | 200K | — |

### ProxyAPI (`proxy_api.py`, бот)
GPT-4.1 Nano/Mini/Full, GPT-4o Mini/Full, o4-mini, GPT-3.5 Turbo

### GenAPI (`gen_api.py`, бот)
GPT-4.1 Mini, GPT-4o, Claude Sonnet 4.5, Gemini 2.5 Flash, DeepSeek Chat, DeepSeek R1
