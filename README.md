# PromptingAIbot

Набор CLI-скриптов и Telegram-бот для работы с несколькими AI-провайдерами: **Z.AI**, **ProxyAPI**, **GenAPI**.

## Структура проекта

```
.
├── bot.py                      # Telegram-бот (aiogram 3)
├── config.py                   # Провайдеры, модели, цены, токены
├── context_manager.py          # In-memory контекст диалога на пользователя
├── openai_client.py            # Единый OpenAI-совместимый HTTP-клиент
├── ai_direct.py                # Интерактивный CLI с историей и сохранением сессии
├── prompt_engineering_demo.py  # Демо prompt engineering: базовый vs few-shot промпт
├── zai_direct.py               # CLI — Z.AI (GLM-модели)
├── proxy_api.py                # CLI — ProxyAPI → OpenAI GPT
├── gen_api.py                  # CLI — GenAPI (GPT / Claude / Gemini / DeepSeek)
├── prompts.json                # Системные промпты для ai_direct.py
├── session.json                # Сохранённая сессия ai_direct.py (создаётся автоматически)
├── artifact_README.md          # Артефакт prompt_engineering_demo.py (создаётся автоматически)
├── .env                        # Секреты (не коммитить)
├── .env.example                # Шаблон .env
├── requirements.txt            # Зависимости
└── .gitignore
```

## Быстрый старт

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt

cp .env.example .env
# заполни .env своими ключами
```

## .env

```env
BOT_TOKEN=your_telegram_bot_token

ZAI_API_KEY=...        # https://z.ai
PROXY_API_KEY=...      # https://proxyapi.ru
GEN_API_KEY=...        # https://gen-api.ru
```

Получить ключи:
- Z.AI — [z.ai](https://z.ai)
- ProxyAPI — [proxyapi.ru](https://proxyapi.ru)
- GenAPI — [gen-api.ru](https://gen-api.ru)
- Telegram Bot Token — [@BotFather](https://t.me/BotFather)

---

## CLI-скрипты

### ai_direct.py — интерактивный CLI с историей

Основной скрипт для диалога с моделью. Поддерживает выбор провайдера, модели, температуры и системных промптов из `prompts.json`. Сохраняет сессию между запусками.

```bash
python ai_direct.py
```

Шаги при запуске:
1. Если найден `session.json` — предложит продолжить предыдущую сессию
2. Выбор провайдера (Z.AI / ProxyAPI / GenAPI)
3. Выбор модели из списка
4. Настройка температуры
5. Выбор системных промптов из `prompts.json` (можно несколько через запятую, или `0` — без промпта)

Команды в диалоге:

| Команда | Действие |
|---------|----------|
| `/model` | Сменить провайдера, модель и температуру |
| `/new` | Очистить историю (промпты сохраняются) |
| `/exit` | Выйти и сохранить сессию в `session.json` |

---

### prompt_engineering_demo.py — демо prompt engineering

Демонстрирует разницу между базовым и улучшенным (few-shot) промптами на бытовых задачах. Запускает оба промпта, сравнивает JSON-ответы и генерирует `artifact_README.md`.

```bash
python prompt_engineering_demo.py
```

Шаги при запуске:
1. Выбор бытовой задачи из списка (вода, скидка, бот, зарядка, покупки)
2. Выбор провайдера и модели
3. Запуск базового промпта (роль → контекст → задача → формат)
4. Запуск улучшенного промпта (+ few-shot пример)
5. Сравнение ответов по 3 критериям: JSON-формат, полезность steps, лаконичность notes
6. Генерация `artifact_README.md` на основе лучшего ответа

Параметры фиксированы: `temperature=0.2`.

---

### zai_direct.py / proxy_api.py / gen_api.py — одиночные запросы

Простые скрипты для одного запроса к конкретному провайдеру.

```bash
python zai_direct.py   # Z.AI (GLM-модели, есть бесплатные)
python proxy_api.py    # ProxyAPI → OpenAI GPT
python gen_api.py      # GenAPI → GPT / Claude / Gemini / DeepSeek
```

Каждый скрипт интерактивно предлагает:
1. Выбрать модель из списка
2. Ввести system message (опционально)
3. Ввести запрос
4. Задать temperature и max_tokens

---

## Telegram-бот

```bash
python bot.py
```

### Команды

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие + мастер настройки сессии |
| `/setup` | Выбрать провайдера, модель, temperature, max_tokens |
| `/info` | Текущие настройки сессии |
| `/clear` | Очистить историю диалога |
| `/report` | Отчёт о прогонах моделей |
| `/help` | Справка по командам |

Написать `очистить контекст` — тоже сбрасывает историю.

### Логика бота

- Каждый пользователь имеет свой контекст (последние 20 сообщений, in-memory).
- `/setup` сбрасывает контекст и позволяет сменить провайдера/модель/параметры.
- Ошибка 402 (недостаточно средств) показывается понятным сообщением.

### /report — отчёт о прогонах

```
#<run> <Модель> [<Провайдер>]
  t=<temperature> max=<max_tokens> | <эффект> | <finish_reason>
  токены: <total> (in <prompt> / out <completion>) | <стоимость ₽>
```

Эффект по температуре: `t < 0.4` → `сжато/факт` | `0.4–0.8` → `баланс` | `t > 0.8` → `креатив`

---

## Провайдеры и модели

### Z.AI

Base URL: `https://api.z.ai/api/paas/v4/`

| Модель | Контекст | Бесплатно | Цена вход | Цена выход |
|--------|----------|-----------|-----------|------------|
| GLM-4.7-Flash | 200K | ✅ | 0 ₽ | 0 ₽ |
| GLM-4.5-Flash | 200K | ✅ | 0 ₽ | 0 ₽ |
| GLM-4.7 | 200K | — | 0.15 ₽/1К | 0.55 ₽/1К |
| GLM-4.5 | 128K | — | 0.15 ₽/1К | 0.55 ₽/1К |
| GLM-5 | 200K | — | 0.25 ₽/1К | 0.80 ₽/1К |

### ProxyAPI

Base URL: `https://api.proxyapi.ru/openai/v1`

| Модель | Контекст | Цена вход | Цена выход |
|--------|----------|-----------|------------|
| GPT-4.1 Nano | 1M | 0.026 ₽/1К | 0.104 ₽/1К |
| GPT-4.1 Mini | 1M | 0.104 ₽/1К | 0.413 ₽/1К |
| GPT-4.1 | 1M | 0.516 ₽/1К | 2.062 ₽/1К |
| GPT-4o Mini | 128K | 0.039 ₽/1К | 0.155 ₽/1К |
| GPT-4o | 128K | 0.645 ₽/1К | 2.577 ₽/1К |
| GPT-3.5 Turbo | 16K | 0.129 ₽/1К | 0.387 ₽/1К |

### GenAPI

Base URL: `https://proxy.gen-api.ru/v1`

> GenAPI использует дефисы вместо точек в ID моделей (`gpt-4-1`, `gemini-2-5-flash`).

| Модель | ID в API | Контекст | Цена вход | Цена выход |
|--------|----------|----------|-----------|------------|
| GPT-4.1 Mini | `gpt-4-1-mini` | 1M | 0.01 ₽/1К | 0.04 ₽/1К |
| GPT-4.1 | `gpt-4-1` | 1M | 0.40 ₽/1К | 1.60 ₽/1К |
| GPT-4o | `gpt-4o` | 128K | 0.50 ₽/1К | 2.00 ₽/1К |
| Claude Sonnet 4.5 | `claude-sonnet-4-5` | 200K | 0.80 ₽/1К | 3.00 ₽/1К |
| Gemini 2.5 Flash | `gemini-2-5-flash` | 1M | 0.06 ₽/1К | 0.50 ₽/1К |
| DeepSeek Chat | `deepseek-chat` | 64K | 0.07 ₽/1К | 0.105 ₽/1К |
| DeepSeek R1 | `deepseek-r1` | 64K | 0.30 ₽/1К | 1.50 ₽/1К |

---

## Архитектура

```
ai_direct.py / prompt_engineering_demo.py / bot.py
  ├── config.py          — PROVIDERS dict (ключи, URL, модели, цены)
  ├── context_manager.py — _store: dict[user_id → session]  (только bot.py)
  └── openai_client.py   — openai.OpenAI(base_url=...) → chat()
```

Все три провайдера используют OpenAI-совместимый API — один клиент работает для всех.
`proxy_api.py` и `gen_api.py` используют `requests` напрямую (без SDK).
