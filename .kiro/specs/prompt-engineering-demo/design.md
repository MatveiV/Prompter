# Дизайн: prompt-engineering-demo

## Обзор

`prompt_engineering_demo.py` — интерактивный CLI-скрипт, демонстрирующий разницу между базовым и улучшенным (few-shot) промптами на бытовых мини-задачах. Скрипт формирует два промпта, отправляет их через `openai_client.chat()`, валидирует JSON-ответы, сравнивает результаты и генерирует `artifact_README.md`.

Скрипт намеренно самодостаточен: все задачи и промпты хранятся внутри него, внешние файлы (кроме `config.py` и `openai_client.py`) не используются.

## Архитектура

### Модули и зависимости

```
prompt_engineering_demo.py
├── config.py          (PROVIDERS — провайдеры и модели)
├── openai_client.py   (chat() — унифицированный HTTP-клиент)
└── artifact_README.md (генерируется в текущей директории)
```

Скрипт не импортирует `prompts.json` и не зависит от `ai_direct.py` — он использует их только как образец стиля.

### Поток выполнения

```mermaid
flowchart TD
    A[Запуск скрипта] --> B[Отобразить список задач]
    B --> C{Ввод номера задачи}
    C -- невалидный --> B
    C -- валидный --> D[Выбор провайдера]
    D --> E[Выбор модели]
    E --> F[Зафиксировать параметры\ntemperature=0.2]
    F --> G[Сформировать Base_Prompt]
    G --> H[Сформировать Enhanced_Prompt]
    H --> I[Отправить Base_Prompt → chat()]
    I --> J[Отправить Enhanced_Prompt → chat()]
    J --> K[Валидировать оба ответа]
    K --> L[Сравнить ответы]
    L --> M[Вывести таблицу сравнения]
    M --> N[Выбрать итоговый ответ]
    N --> O[Записать artifact_README.md]
    O --> P[Отобразить путь к файлу]
```

## Компоненты и интерфейсы

### Структура данных TASKS

```python
TASKS: dict[str, dict] = {
    "1": {
        "key": "water_reminder",
        "label": "Напоминание пить воду",
        "role": "Ты — помощник по здоровому образу жизни.",
        "context": "Пользователь хочет выработать привычку пить воду регулярно.",
        "task": "Составь план напоминаний пить воду в течение дня.",
        "few_shot_example": {
            "title": "Пример: план питья воды",
            "steps": ["08:00 — стакан воды после пробуждения", "..."],
            "notes": ["Норма — 8 стаканов в день", "..."]
        }
    },
    "2": { "key": "discount_calc",   "label": "Расчёт скидки",         ... },
    "3": { "key": "welcome_bot",     "label": "Приветственный бот",     ... },
    "4": { "key": "morning_workout", "label": "План утренней зарядки",  ... },
    "5": { "key": "shopping_list",   "label": "Список покупок",         ... },
}
```

Каждая задача содержит: `key`, `label`, `role`, `context`, `task`, `few_shot_example`.

### Структура промптов

**Base_Prompt** (системное сообщение):
```
Роль: {role}
Контекст: {context}
Задача: {task}
Формат ответа: верни строго JSON без пояснений:
{"title": "...", "steps": ["...", "..."], "notes": ["...", "..."]}
```

**Enhanced_Prompt** (системное сообщение):
```
{Base_Prompt}

Пример корректного ответа:
{"title": "{few_shot.title}", "steps": [...], "notes": [...]}
```

Пользовательское сообщение для обоих промптов одинаковое: `"Выполни задачу."`.

### Сигнатуры ключевых функций

```python
def pick_task() -> tuple[str, dict]:
    """Интерактивный выбор задачи. Возвращает (task_key, task_dict)."""

def pick_provider_and_model() -> tuple[str, str, dict]:
    """Выбор провайдера и модели. Возвращает (provider_key, model_id, model_dict)."""

def build_base_prompt(task: dict) -> str:
    """Формирует системный промпт по схеме роль→контекст→задача→формат."""

def build_enhanced_prompt(task: dict) -> str:
    """Расширяет Base_Prompt few-shot примером из task['few_shot_example']."""

def parse_response(raw: str) -> tuple[dict | None, str]:
    """
    Парсит ответ модели. Извлекает JSON из markdown-блоков если нужно.
    Возвращает (parsed_dict | None, status) где status ∈ {"valid", "incomplete", "invalid"}.
    """

def compare_responses(base: tuple[dict | None, str], enhanced: tuple[dict | None, str]) -> dict:
    """
    Сравнивает два ответа по трём критериям.
    Возвращает ComparisonResult (см. Data Models).
    """

def select_winner(
    base_parsed: dict | None, base_status: str,
    enhanced_parsed: dict | None, enhanced_status: str
) -> tuple[dict | None, str]:
    """
    Выбирает итоговый ответ: Enhanced если валиден, иначе Base.
    Возвращает (parsed_dict | None, source) где source ∈ {"enhanced", "base"}.
    """

def write_artifact(
    task: dict, model_label: str,
    winner: dict | None, winner_raw: str, winner_status: str
) -> str:
    """Записывает artifact_README.md. Возвращает путь к файлу."""

def run_demo(task: dict, provider_key: str, model_id: str, model_dict: dict) -> None:
    """Основной оркестратор: формирует промпты, вызывает API, сравнивает, пишет артефакт."""
```

## Модели данных

### ParsedResponse

```python
# Результат parse_response()
{
    "parsed": dict | None,   # распарсенный JSON или None
    "raw": str,              # исходная строка ответа
    "status": str,           # "valid" | "incomplete" | "invalid"
    "usage": dict,           # токены из openai_client.chat()
}
```

### ComparisonResult

```python
{
    "base": {
        "json_valid": bool,
        "steps_count": int,       # len(parsed["steps"]) или 0
        "avg_notes_len": float,   # среднее len(s) по notes или 0.0
    },
    "enhanced": {
        "json_valid": bool,
        "steps_count": int,
        "avg_notes_len": float,
    },
    "winner": {
        "json_valid": str,        # "base" | "enhanced" | "tie"
        "steps_count": str,
        "avg_notes_len": str,     # меньше = лаконичнее → "base" если base < enhanced
    }
}
```

### Структура artifact_README.md

```markdown
# {title}

> Задача: {task_label}
> Модель: {model_label}
> Дата: {YYYY-MM-DD HH:MM:SS}
> Источник: {enhanced | base}

## Шаги

1. {steps[0]}
2. {steps[1]}
...

## Примечания

- {notes[0]}
- {notes[1]}
...
```

При невалидном ответе:

```markdown
# Ошибка парсинга

> Задача: {task_label}
> Модель: {model_label}
> Дата: {YYYY-MM-DD HH:MM:SS}
> Статус: {status}

## Сырой ответ модели

{raw_text}
```

## Алгоритм сравнения ответов

```
compare_responses(base, enhanced):
  для каждого ответа вычислить:
    json_valid  = (status == "valid")
    steps_count = len(parsed["steps"]) if parsed else 0
    avg_notes_len = mean(len(s) for s in parsed["notes"]) if parsed and parsed["notes"] else 0.0

  winner.json_valid:
    если оба валидны или оба невалидны → "tie"
    иначе → тот, кто валиден

  winner.steps_count:
    больше шагов → лучше (больше деталей)
    если равно → "tie"

  winner.avg_notes_len:
    меньше средняя длина → лаконичнее → лучше
    если равно → "tie"
```

Логика выбора итогового ответа (`select_winner`):
- Enhanced валиден → использовать Enhanced
- Enhanced невалиден, Base валиден → использовать Base
- Оба невалидны → использовать Enhanced (как «более продвинутый»), записать сырой текст

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Валидный номер задачи возвращает соответствующую задачу

*Для любого* целого числа `n` из диапазона `[1, len(TASKS)]`, функция выбора задачи должна возвращать объект Task с ключом `str(n)`.

**Validates: Requirements 1.2**

---

### Property 2: Невалидный номер задачи сигнализирует об ошибке

*Для любого* значения, не входящего в диапазон допустимых номеров задач (строки, числа вне диапазона, пустая строка), функция валидации ввода должна возвращать `False` или поднимать исключение.

**Validates: Requirements 1.3**

---

### Property 3: Список моделей соответствует провайдеру

*Для любого* валидного ключа провайдера из `PROVIDERS`, функция получения моделей должна возвращать список, идентичный `PROVIDERS[key]["models"]`.

**Validates: Requirements 2.2**

---

### Property 4: Base_Prompt содержит все компоненты схемы и требование JSON

*Для любой* задачи из `TASKS`, результат `build_base_prompt(task)` должен содержать: роль (`task["role"]`), контекст (`task["context"]`), задачу (`task["task"]`), и строку с описанием JSON-формата (`title`, `steps`, `notes`).

**Validates: Requirements 3.1, 3.3**

---

### Property 5: Enhanced_Prompt строго длиннее Base_Prompt

*Для любой* задачи из `TASKS`, `len(build_enhanced_prompt(task)) > len(build_base_prompt(task))` — Enhanced содержит всё, что есть в Base, плюс few-shot пример.

**Validates: Requirements 3.2**

---

### Property 6: Оба вызова API используют одинаковые параметры

*Для любой* пары (provider_key, model_id), оба вызова `chat()` должны получать одинаковые значения `model_id` и `temperature=0.2`.

**Validates: Requirements 4.3, 2.5**

---

### Property 7: parse_response никогда не падает с необработанным исключением

*Для любой* строки (включая пустую, невалидный JSON, бинарные данные), `parse_response(s)` должна возвращать кортеж `(None | dict, status)` без поднятия исключения.

**Validates: Requirements 5.1**

---

### Property 8: Валидация JSON возвращает корректный статус

*Для любой* строки `s`:
- если `s` не парсится как JSON → статус `"invalid"`
- если парсится, но отсутствует хотя бы один из ключей `title`, `steps`, `notes` → статус `"incomplete"`
- если все три ключа присутствуют с правильными типами → статус `"valid"`

**Validates: Requirements 5.2, 5.3, 5.4**

---

### Property 9: Извлечение JSON из markdown-блоков

*Для любой* строки, содержащей валидный JSON внутри ` ```json ... ``` `, функция `parse_response` должна возвращать тот же результат, что и для строки с «голым» JSON.

**Validates: Requirements 5.5**

---

### Property 10: compare_responses возвращает корректные метрики

*Для любых* двух `ParsedResponse`, `compare_responses` должна возвращать `ComparisonResult` где:
- `steps_count` равен `len(parsed["steps"])` (или 0 если невалиден)
- `avg_notes_len` равен среднему `len(s)` по `notes` (или 0.0)
- `winner` по каждому критерию корректно определён

**Validates: Requirements 6.1, 6.3, 6.4, 6.5, 6.6**

---

### Property 11: select_winner выбирает Enhanced если он валиден

*Для любой* пары статусов `(base_status, enhanced_status)`:
- если `enhanced_status == "valid"` → источник `"enhanced"`
- если `enhanced_status != "valid"` и `base_status == "valid"` → источник `"base"`
- если оба невалидны → источник `"enhanced"`

**Validates: Requirements 7.1**

---

### Property 12: artifact_README.md содержит все обязательные секции и метаданные

*Для любого* валидного `ParsedResponse` и набора метаданных (task_label, model_label, datetime), содержимое сгенерированного файла должно включать: `title`, все элементы `steps`, все элементы `notes`, название задачи, имя модели, дату генерации.

**Validates: Requirements 7.3, 7.4**

---

## Обработка ошибок

| Ситуация | Поведение |
|---|---|
| Невалидный номер задачи | Повторный запрос ввода |
| Отсутствует API-ключ провайдера | Сообщение об ошибке + `sys.exit(1)` |
| `chat()` поднимает исключение | Вывод текста ошибки + `sys.exit(1)` |
| Ответ не является JSON | Статус `"invalid"`, сравнение продолжается |
| JSON без обязательных ключей | Статус `"incomplete"`, сравнение продолжается |
| Итоговый ответ невалиден | Запись сырого текста в артефакт с пометкой |

## Стратегия тестирования

### Подход

Используется двойная стратегия: unit-тесты для конкретных примеров и граничных случаев, property-тесты для универсальных свойств.

### Unit-тесты (примеры и граничные случаи)

- TASKS содержит ровно 5 задач с нужными ключами (Req 1.1, 1.4)
- Список провайдеров совпадает с ключами `config.PROVIDERS` (Req 2.1)
- `temperature=0.2` зафиксирована в вызове `chat()` (Req 2.3, 2.5)
- Оба вызова `chat()` выполняются (Req 4.1, 4.2) — через mock
- Отсутствие API-ключа вызывает `sys.exit` (Req 2.4) — граничный случай
- `chat()` с исключением вызывает `sys.exit` (Req 4.4) — граничный случай
- Невалидный JSON → статус `"invalid"` (Req 5.3) — граничный случай
- JSON без ключей → статус `"incomplete"` (Req 5.4) — граничный случай
- Невалидный итоговый ответ → артефакт с пометкой (Req 7.5) — граничный случай
- Файл `artifact_README.md` создаётся (Req 7.2)

### Property-тесты (универсальные свойства)

Библиотека: **Hypothesis** (Python).
Каждый тест запускается минимум 100 итераций (настройка `@settings(max_examples=100)`).

| Тест | Свойство | Тег |
|---|---|---|
| `test_valid_task_selection` | Property 1 | `Feature: prompt-engineering-demo, Property 1` |
| `test_invalid_task_input` | Property 2 | `Feature: prompt-engineering-demo, Property 2` |
| `test_models_match_provider` | Property 3 | `Feature: prompt-engineering-demo, Property 3` |
| `test_base_prompt_structure` | Property 4 | `Feature: prompt-engineering-demo, Property 4` |
| `test_enhanced_longer_than_base` | Property 5 | `Feature: prompt-engineering-demo, Property 5` |
| `test_api_calls_same_params` | Property 6 | `Feature: prompt-engineering-demo, Property 6` |
| `test_parse_never_raises` | Property 7 | `Feature: prompt-engineering-demo, Property 7` |
| `test_validation_status` | Property 8 | `Feature: prompt-engineering-demo, Property 8` |
| `test_markdown_json_extraction` | Property 9 | `Feature: prompt-engineering-demo, Property 9` |
| `test_compare_metrics` | Property 10 | `Feature: prompt-engineering-demo, Property 10` |
| `test_select_winner_logic` | Property 11 | `Feature: prompt-engineering-demo, Property 11` |
| `test_artifact_content` | Property 12 | `Feature: prompt-engineering-demo, Property 12` |

Каждый property-тест реализует ровно одно свойство из раздела Correctness Properties.
