"""
prompter.py — A/B-тестирование техник prompt engineering.
Запуск: python prompter.py

Интерактивно запрашивает задачу, провайдера, модель, temperature, max_tokens
и набор техник для сравнения. Поддерживаемые техники:
  - zero-shot        — прямой запрос без примеров
  - few-shot         — запрос с примером корректного ответа
  - chain-of-thought — запрос с пошаговым рассуждением (CoT)
  - role-based       — запрос с явным указанием роли эксперта

Все техники запускаются с одинаковыми параметрами модели.
Результаты ранжируются и сохраняются в artifact_YYYYMMDD_HHMMSS.md:
  - параметры запуска (модель, temperature, max_tokens)
  - промпты и ответы по каждой технике
  - стоимость каждого запроса в ₽
  - сводная таблица сравнения с рангами
  - детальный разбор каждой техники
"""
import json
import os
import re
import sys
from datetime import datetime

import openai_client
from config import PROVIDERS

# ─── Задачи ───────────────────────────────────────────────────────────────────

TASKS: dict[str, dict] = {
    "1": {
        "key": "water_reminder",
        "label": "Напоминание пить воду",
        "role": "Ты — персональный тренер по здоровому образу жизни с 10-летним опытом.",
        "context": "Пользователь хочет выработать привычку пить воду регулярно в течение дня.",
        "task": "Составь конкретный план напоминаний пить воду на один день.",
        "cot_hint": "Сначала определи оптимальные временные интервалы, затем учти физиологию (утро, до/после еды, вечер), потом сформируй итоговый план.",
        "few_shot_example": {
            "title": "План питья воды на день",
            "steps": [
                "07:00 — стакан воды сразу после пробуждения",
                "09:00 — стакан воды перед завтраком",
                "11:00 — стакан воды в середине утра",
                "13:00 — стакан воды перед обедом",
                "15:00 — стакан воды после обеда",
                "17:00 — стакан воды в середине дня",
                "19:00 — стакан воды перед ужином",
                "21:00 — стакан воды за час до сна",
            ],
            "notes": [
                "Норма — 8 стаканов (около 2 литров) в день",
                "Поставь напоминания в телефоне",
                "Держи бутылку воды на виду",
            ],
        },
    },
    "2": {
        "key": "discount_calc",
        "label": "Расчёт скидки",
        "role": "Ты — финансовый консультант, специализирующийся на бытовой экономии.",
        "context": "Пользователь хочет быстро посчитать итоговую цену товара со скидкой.",
        "task": "Объясни пошагово, как рассчитать цену товара с учётом скидки в процентах.",
        "cot_hint": "Сначала выведи математическую формулу, затем разбей её на понятные шаги, потом приведи числовой пример.",
        "few_shot_example": {
            "title": "Как рассчитать цену со скидкой",
            "steps": [
                "Узнай исходную цену товара (например, 1000 ₽)",
                "Узнай размер скидки в процентах (например, 20%)",
                "Вычисли сумму скидки: 1000 × 0.20 = 200 ₽",
                "Вычти скидку из цены: 1000 − 200 = 800 ₽",
                "Итоговая цена: 800 ₽",
            ],
            "notes": [
                "Формула: итог = цена × (1 − скидка/100)",
                "Для скидки 20%: умножь цену на 0.8",
                "Проверь, не суммируются ли несколько скидок",
            ],
        },
    },
    "3": {
        "key": "welcome_bot",
        "label": "Приветственный бот",
        "role": "Ты — senior UX-копирайтер с опытом разработки диалоговых интерфейсов.",
        "context": "Пользователь хочет настроить приветственное сообщение для своего чат-бота.",
        "task": "Составь план создания эффективного приветственного сообщения для чат-бота.",
        "cot_hint": "Сначала определи цель бота, затем продумай структуру сообщения (приветствие → возможности → призыв к действию), потом сформулируй финальный текст.",
        "few_shot_example": {
            "title": "Приветственное сообщение для бота",
            "steps": [
                "Определи цель бота (поддержка, продажи, информация)",
                "Напиши короткое приветствие с именем бота",
                "Объясни, что умеет бот (2–3 пункта)",
                "Добавь призыв к действию (например, 'Напиши свой вопрос')",
                "Протестируй сообщение на реальных пользователях",
            ],
            "notes": [
                "Приветствие должно быть не длиннее 3–4 предложений",
                "Используй дружелюбный тон",
                "Укажи, как связаться с человеком если бот не помог",
            ],
        },
    },
    "4": {
        "key": "morning_workout",
        "label": "План утренней зарядки",
        "role": "Ты — сертифицированный фитнес-тренер, специализирующийся на домашних тренировках.",
        "context": "Пользователь хочет начать делать утреннюю зарядку дома без оборудования.",
        "task": "Составь план утренней зарядки на 10–15 минут для начинающих.",
        "cot_hint": "Сначала определи группы мышц для разминки, затем подбери упражнения по принципу от лёгкого к сложному, потом распредели время.",
        "few_shot_example": {
            "title": "Утренняя зарядка на 10 минут",
            "steps": [
                "1 мин — потягивания лёжа в кровати",
                "2 мин — вращения шеей, плечами, запястьями",
                "2 мин — наклоны в стороны и вперёд стоя",
                "2 мин — приседания (2 подхода по 10 раз)",
                "2 мин — отжимания от пола (2 подхода по 5–8 раз)",
                "1 мин — планка (2 подхода по 20–30 секунд)",
            ],
            "notes": [
                "Делай зарядку сразу после пробуждения",
                "Не форсируй нагрузку — важна регулярность",
                "Пей стакан воды до и после зарядки",
            ],
        },
    },
    "5": {
        "key": "shopping_list",
        "label": "Список покупок",
        "role": "Ты — эксперт по организации быта и осознанному потреблению.",
        "context": "Пользователь хочет составить эффективный список покупок на неделю.",
        "task": "Объясни пошагово, как составить список покупок на неделю, чтобы ничего не забыть и не купить лишнего.",
        "cot_hint": "Сначала продумай планирование меню, затем инвентаризацию холодильника, потом структурирование списка по категориям.",
        "few_shot_example": {
            "title": "Как составить список покупок на неделю",
            "steps": [
                "Составь меню на 7 дней (завтрак, обед, ужин)",
                "Выпиши все ингредиенты из меню",
                "Проверь холодильник и шкафы — вычеркни то, что уже есть",
                "Добавь регулярные товары (хлеб, молоко, яйца)",
                "Сгруппируй список по отделам магазина",
                "Запиши список в телефон или распечатай",
            ],
            "notes": [
                "Ходи в магазин не голодным",
                "Придерживайся списка — это экономит деньги",
                "Обновляй список раз в неделю",
            ],
        },
    },
}

# ─── Техники промптинга ───────────────────────────────────────────────────────

TECHNIQUES: dict[str, str] = {
    "1": "zero-shot",
    "2": "few-shot",
    "3": "chain-of-thought",
    "4": "role-based",
}

JSON_FORMAT = '{"title": "...", "steps": ["...", "..."], "notes": ["...", "..."]}'

# ─── Вспомогательные функции ──────────────────────────────────────────────────

def sep(char: str = "─", width: int = 60) -> None:
    print(char * width)


def ask(prompt: str, default: str = "") -> str:
    val = input(prompt).strip()
    return val if val else default


def get_float(prompt: str, default: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(ask(prompt, str(default)))))
    except ValueError:
        return default


def get_int(prompt: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(ask(prompt, str(default)))))
    except ValueError:
        return default


def calc_cost(usage: dict, model: dict) -> float:
    p_in  = model.get("price_in", 0.0)
    p_out = model.get("price_out", 0.0)
    return (usage.get("prompt_tokens", 0) / 1000 * p_in +
            usage.get("completion_tokens", 0) / 1000 * p_out)

# ─── Выбор задачи ─────────────────────────────────────────────────────────────

def pick_task() -> dict:
    sep("═")
    print("  ВЫБОР ЗАДАЧИ")
    sep("═")
    for key, t in TASKS.items():
        print(f"  {key}. {t['label']}")
    sep()
    while True:
        choice = input("  Номер задачи: ").strip()
        if choice in TASKS:
            return TASKS[choice]
        print(f"  Неверный номер. Введите от 1 до {len(TASKS)}.")

# ─── Выбор провайдера и модели ────────────────────────────────────────────────

def pick_provider_and_model() -> tuple[str, str, dict]:
    sep("═")
    print("  ВЫБОР ПРОВАЙДЕРА")
    sep("═")
    p_keys = list(PROVIDERS.keys())
    for i, k in enumerate(p_keys, 1):
        print(f"  {i}. {PROVIDERS[k]['name']}")
    sep()
    while True:
        choice = ask("  Провайдер [1]: ", "1")
        try:
            p_key = p_keys[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print("  Неверный номер.")

    if not PROVIDERS[p_key].get("api_key"):
        print(f"  Ошибка: API-ключ для {PROVIDERS[p_key]['name']} не найден в .env")
        sys.exit(1)

    models = PROVIDERS[p_key]["models"]
    sep()
    print(f"  МОДЕЛИ — {PROVIDERS[p_key]['name']}")
    sep()
    print(f"  {'#':<4} {'Модель':<28} {'Контекст':<10} {'Бесплатно':<12} {'Температура':<14} Макс. токенов")
    sep()
    for i, m in enumerate(models, 1):
        free_tag = "да" if m.get("free") else "нет"
        tlo, thi = m.get("temp_range", (0.0, 2.0))
        print(f"  {i:<4} {m['label']:<28} {m.get('context','?'):<10} {free_tag:<12} {tlo}–{thi:<10} {m.get('max_tokens_limit','?')}")
    sep()
    while True:
        choice = ask("  Модель [1]: ", "1")
        try:
            model = models[int(choice) - 1]
            break
        except (ValueError, IndexError):
            print("  Неверный номер.")

    return p_key, model["id"], model

# ─── Выбор параметров модели ──────────────────────────────────────────────────

def pick_params(model: dict) -> tuple[float, int]:
    lo, hi = model.get("temp_range", (0.0, 2.0))
    max_limit = model.get("max_tokens_limit", 4096)
    sep()
    print("  ПАРАМЕТРЫ ЗАПРОСА")
    sep()
    print(f"  Рекомендуется temperature=0.2 для структурированного JSON-вывода.")
    print(f"  Значения выше 1.0 могут привести к нечитаемым ответам.")
    temperature = get_float(f"  Temperature [{lo}–{hi}], по умолчанию 0.2: ", 0.2, lo, hi)
    if temperature > 1.0:
        print(f"  Предупреждение: temperature={temperature} очень высокая — модель может вернуть мусор вместо JSON.")
        confirm = ask("  Продолжить? [y/N]: ", "n").lower()
        if confirm != "y":
            temperature = get_float(f"  Temperature [{lo}–{hi}], по умолчанию 0.2: ", 0.2, lo, hi)
    max_tokens  = get_int(f"  Max tokens [1–{max_limit}], по умолчанию 512: ", 512, 1, max_limit)
    return temperature, max_tokens

# ─── Выбор техник ─────────────────────────────────────────────────────────────

def pick_techniques() -> list[str]:
    sep()
    print("  ТЕХНИКИ ПРОМПТИНГА (A/B-тест)")
    sep()
    for key, name in TECHNIQUES.items():
        print(f"  {key}. {name}")
    sep()
    print("  Введите номера через запятую (например: 1,2,3) или Enter для всех")
    raw = ask("  Техники [все]: ", "")
    if not raw:
        return list(TECHNIQUES.values())
    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part in TECHNIQUES:
            selected.append(TECHNIQUES[part])
    return selected if selected else list(TECHNIQUES.values())

# ─── Построение промптов по технике ──────────────────────────────────────────

def build_prompt(task: dict, technique: str) -> str:
    # Базовая схема по заданию: роль → контекст → задача → формат ответа
    role_line    = f"Роль: {task['role']}"
    context_line = f"Контекст: {task['context']}"
    task_line    = f"Задача: {task['task']}"
    format_line  = f"Формат ответа: верни строго JSON без пояснений и без markdown:\n{JSON_FORMAT}"

    if technique == "zero-shot":
        # Схема без примера и без подсказок
        return "\n".join([role_line, context_line, task_line, format_line])

    if technique == "few-shot":
        # Схема + мини-пример (итерация качества по заданию п.4)
        example = json.dumps(task["few_shot_example"], ensure_ascii=False, indent=2)
        return "\n".join([
            role_line, context_line, task_line, format_line,
            "",
            "Пример корректного ответа:",
            example,
        ])

    if technique == "chain-of-thought":
        # Схема + явное пошаговое рассуждение
        return "\n".join([
            role_line, context_line, task_line,
            f"Рассуждай пошагово: {task['cot_hint']}",
            format_line,
        ])

    if technique == "role-based":
        # Усиленная роль + контекст + задача + формат
        return "\n".join([
            f"Роль: {task['role']} Отвечай строго как этот эксперт.",
            context_line, task_line, format_line,
        ])

    return "\n".join([role_line, context_line, task_line, format_line])

# ─── Валидация ответа ─────────────────────────────────────────────────────────

def parse_response(raw: str) -> tuple[dict | None, str]:
    """
    Многоуровневое извлечение JSON из ответа модели.
    1. Ищет ```json ... ``` блок
    2. Ищет первый { ... } объект в тексте (жадный поиск)
    3. Пробует весь текст как JSON
    """
    def _try_parse(text: str) -> dict | None:
        try:
            data = json.loads(text)
            if (isinstance(data.get("title"), str)
                    and isinstance(data.get("steps"), list)
                    and isinstance(data.get("notes"), list)):
                return data
        except Exception:
            pass
        return None

    # 1. Markdown-блок ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        result = _try_parse(match.group(1))
        if result:
            return result, "valid"

    # 2. Найти первый { и попробовать разобрать JSON с нарастающей длиной
    #    (ищем самый длинный валидный JSON-объект начиная с первой {)
    start = raw.find("{")
    if start != -1:
        # Попробуем найти закрывающую } методом подсчёта скобок
        depth = 0
        end = -1
        for i, ch in enumerate(raw[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end != -1:
            candidate = raw[start:end]
            result = _try_parse(candidate)
            if result:
                return result, "valid"
            # Поля есть, но неполные
            try:
                data = json.loads(candidate)
                return data, "incomplete"
            except Exception:
                pass

    # 3. Весь текст как JSON
    result = _try_parse(raw.strip())
    if result:
        return result, "valid"

    return None, "invalid"

# ─── Метрики и сравнение ──────────────────────────────────────────────────────

def _metrics(parsed: dict | None, status: str) -> dict:
    valid = status == "valid"
    steps = len(parsed["steps"]) if valid and parsed else 0
    notes = parsed.get("notes", []) if valid and parsed else []
    avg_notes = sum(len(s) for s in notes) / len(notes) if notes else 0.0
    return {"json_valid": valid, "steps_count": steps, "avg_notes_len": avg_notes}


def compare_all(results: list[dict]) -> list[dict]:
    """Добавляет поле 'rank' к каждому результату по сумме баллов."""
    for r in results:
        m = r["metrics"]
        r["score"] = (
            (1 if m["json_valid"] else 0)
            + m["steps_count"] * 0.1
            - m["avg_notes_len"] * 0.001
        )
    ranked = sorted(results, key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
    return results

# ─── Вывод в терминал ─────────────────────────────────────────────────────────

def print_comparison(results: list[dict]) -> None:
    sep("═")
    print("  A/B СРАВНЕНИЕ ТЕХНИК")
    sep("═")
    cols = [20, 10, 8, 12, 14, 10, 8]
    header = ("Техника", "Статус", "Ранг", "Шагов", "Ср.длина notes", "Токены", "Стоимость")
    print("  " + "  ".join(h.ljust(cols[i]) for i, h in enumerate(header)))
    sep()
    for r in sorted(results, key=lambda x: x["rank"]):
        m = r["metrics"]
        cost_str = f"{r['cost']:.4f}₽" if r["cost"] > 0 else "бесплатно"
        row = (
            r["technique"],
            r["status"],
            str(r["rank"]),
            str(m["steps_count"]),
            f"{m['avg_notes_len']:.1f}",
            str(r["usage"].get("total_tokens", "?")),
            cost_str,
        )
        print("  " + "  ".join(str(v).ljust(cols[i]) for i, v in enumerate(row)))
    sep("═")

# ─── Генерация артефакта ──────────────────────────────────────────────────────

def _technique_section(r: dict) -> str:
    m = r["metrics"]
    cost_str = f"{r['cost']:.4f} ₽" if r["cost"] > 0 else "бесплатно"
    u = r["usage"]
    lines = [
        f"### Техника: {r['technique']} (ранг #{r['rank']})",
        "",
        f"| Параметр | Значение |",
        f"| --- | --- |",
        f"| Статус JSON | {r['status']} |",
        f"| Шагов (steps) | {m['steps_count']} |",
        f"| Ср. длина notes | {m['avg_notes_len']:.1f} симв. |",
        f"| Токены вход | {u.get('prompt_tokens','?')} |",
        f"| Токены выход | {u.get('completion_tokens','?')} |",
        f"| Токены всего | {u.get('total_tokens','?')} |",
        f"| Стоимость | {cost_str} |",
        "",
        "**Промпт (system):**",
        "",
        f"```\n{r['prompt']}\n```",
        "",
        "**Ответ модели:**",
        "",
        f"```\n{r['raw']}\n```",
    ]
    if r["status"] == "valid" and r["parsed"]:
        p = r["parsed"]
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(p["steps"]))
        notes_md = "\n".join(f"- {n}" for n in p["notes"])
        lines += [
            "",
            "**Распознанный результат:**",
            "",
            f"**{p['title']}**",
            "",
            steps_md,
            "",
            notes_md,
        ]
    return "\n".join(lines)


def _iteration_comparison_md(results: list[dict]) -> str:
    """Пункт 5 задания: сравнение 'до' (zero-shot) и 'после' (few-shot) итерации."""
    before = next((r for r in results if r["technique"] == "zero-shot"), None)
    after  = next((r for r in results if r["technique"] == "few-shot"), None)
    if not before and not after:
        return "_Ни zero-shot, ни few-shot не были выбраны — сравнение итерации недоступно._\n"
    if not before:
        return "_zero-shot не выбран — добавьте его для сравнения итерации._\n"
    if not after:
        return "_few-shot не выбран — добавьте его для сравнения итерации._\n"

    def yn(val: bool) -> str:
        return "да ✅" if val else "нет ❌"

    bm, am = before["metrics"], after["metrics"]

    # Полезность шагов: больше шагов = лучше
    steps_verdict = "few-shot лучше" if am["steps_count"] > bm["steps_count"] else (
        "zero-shot лучше" if bm["steps_count"] > am["steps_count"] else "одинаково")

    # Лаконичность notes: меньше средняя длина = лаконичнее
    notes_verdict = "few-shot лаконичнее" if am["avg_notes_len"] < bm["avg_notes_len"] else (
        "zero-shot лаконичнее" if bm["avg_notes_len"] < am["avg_notes_len"] else "одинаково")

    lines = [
        "| Критерий | До (zero-shot) | После (few-shot) | Итог |",
        "| --- | --- | --- | --- |",
        f"| Соответствие JSON-формату | {yn(bm['json_valid'])} | {yn(am['json_valid'])} | {'улучшилось' if am['json_valid'] and not bm['json_valid'] else 'без изменений'} |",
        f"| Полезность шагов (кол-во) | {bm['steps_count']} | {am['steps_count']} | {steps_verdict} |",
        f"| Лаконичность notes (ср.длина) | {bm['avg_notes_len']:.1f} симв. | {am['avg_notes_len']:.1f} симв. | {notes_verdict} |",
    ]
    return "\n".join(lines)


def _user_readme_md(
    task: dict,
    winner: dict,
    model_label: str,
    human_time: str,
    results: list[dict],
) -> str:
    """Пункт 6 задания: README для пользователя — итоговый ответ + анализ промптов."""
    p = winner.get("parsed")

    # Шапка с параметрами
    header_lines = [
        f"# Результат: {task['label']}",
        "",
        f"> Задача: {task['label']}  ",
        f"> Модель: {model_label}  ",
        f"> Дата: {human_time}  ",
        f"> Лучшая техника: {winner['technique']} (ранг #{winner['rank']})",
        "",
    ]

    # Итоговый ответ победителя
    if p and winner["status"] == "valid":
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(p["steps"]))
        notes_md = "\n".join(f"- {n}" for n in p["notes"])
        result_lines = [
            f"## {p['title']}",
            "",
            "### Шаги",
            "",
            steps_md,
            "",
            "### Примечания",
            "",
            notes_md,
            "",
        ]
    else:
        result_lines = [
            f"## Итоговый ответ",
            "",
            f"_Ответ техники '{winner['technique']}' невалиден (статус: {winner['status']})._",
            "",
        ]

    # Анализ промптов: сводная таблица (пункт 5)
    analysis_lines = [
        "---",
        "",
        "## Анализ промптов (A/B-тест)",
        "",
        "### Сводная таблица",
        "",
        _comparison_table_md(results),
        "",
        "### Сравнение итерации качества (zero-shot → few-shot)",
        "",
        "_Соответствие JSON-формату, полезность шагов, лаконичность notes:_",
        "",
        _iteration_comparison_md(results),
        "",
        "### Формула ранга",
        "",
        "```",
        "score = json_valid × 1.0 + steps_count × 0.1 − avg_notes_len × 0.001",
        "```",
        "",
    ]

    return "\n".join(header_lines + result_lines + analysis_lines)


def _comparison_table_md(results: list[dict]) -> str:
    header = ["Ранг", "Техника", "JSON", "Шагов", "Ср.длина notes", "Токены", "Стоимость"]
    rows = [header, ["---"] * len(header)]
    for r in sorted(results, key=lambda x: x["rank"]):
        m = r["metrics"]
        cost_str = f"{r['cost']:.4f} ₽" if r["cost"] > 0 else "бесплатно"
        rows.append([
            f"#{r['rank']}",
            r["technique"],
            "✅" if m["json_valid"] else "❌",
            str(m["steps_count"]),
            f"{m['avg_notes_len']:.1f}",
            str(r["usage"].get("total_tokens", "?")),
            cost_str,
        ])
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def write_artifact(
    task: dict,
    provider_name: str,
    model_id: str,
    model_label: str,
    temperature: float,
    max_tokens: int,
    results: list[dict],
) -> tuple[str, str]:
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    human_time = now.strftime("%Y-%m-%d %H:%M:%S")
    path = f"artifact_{timestamp}.md"
    readme_path = f"result_{timestamp}.md"

    total_cost = sum(r["cost"] for r in results)
    total_tokens = sum(r["usage"].get("total_tokens", 0) for r in results)
    winner = min(results, key=lambda x: x["rank"])
    all_invalid = all(r["status"] == "invalid" for r in results)

    lines = [
        f"# Prompter A/B Report — {human_time}",
        "",
        "## Параметры запуска",
        "",
        "| Параметр | Значение |",
        "| --- | --- |",
        f"| Задача | {task['label']} |",
        f"| Провайдер | {provider_name} |",
        f"| Модель (label) | {model_label} |",
        f"| Модель (id) | {model_id} |",
        f"| Temperature | {temperature} |",
        f"| Max tokens | {max_tokens} |",
        f"| Техник протестировано | {len(results)} |",
        f"| Токенов всего | {total_tokens} |",
        f"| Стоимость всего | {'бесплатно' if total_cost == 0 else f'{total_cost:.4f} ₽'} |",
        "",
    ]

    if all_invalid:
        lines += [
            "> ⚠️ **Все техники вернули невалидный JSON.**",
            f"> Temperature={temperature} слишком высокая для структурированного вывода.",
            "> Рекомендация: повторите запуск с temperature=0.2",
            "",
        ]

    lines += [
        "---",
        "",
        "## Сводная таблица сравнения",
        "",
        _comparison_table_md(results),
        "",
        "---",
        "",
        "## Сравнение итерации качества (zero-shot → few-shot)",
        "",
        "_Пункт 5: соответствие JSON-формату, полезность шагов, лаконичность notes._",
        "",
        _iteration_comparison_md(results),
        "",
        "---",
        "",
        "## Победитель",
        "",
        f"**Техника:** {winner['technique']}  ",
        f"**Статус:** {winner['status']}  ",
        f"**Шагов:** {winner['metrics']['steps_count']}  ",
        f"**Стоимость:** {('бесплатно' if winner['cost'] == 0 else '{:.4f} ₽'.format(winner['cost']))}",
        "",
        "---",
        "",
        "## Детали по каждой технике",
        "",
    ]

    for r in sorted(results, key=lambda x: x["rank"]):
        lines.append(_technique_section(r))
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Пункт 6: отдельный README для пользователя с анализом промптов
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(_user_readme_md(task, winner, model_label, human_time, results))

    return os.path.abspath(path), os.path.abspath(readme_path)

# ─── Оркестратор ──────────────────────────────────────────────────────────────

def run() -> None:
    print("\n" + "═" * 60)
    print("  PROMPTER — A/B-тест техник промптинга")
    print("═" * 60)

    task = pick_task()
    provider_key, model_id, model_dict = pick_provider_and_model()
    temperature, max_tokens = pick_params(model_dict)
    techniques = pick_techniques()

    model_label = model_dict["label"]
    user_msg = "Выполни задачу."

    results: list[dict] = []

    sep("═")
    print(f"  Запуск {len(techniques)} техник → {model_label} | t={temperature} | max_tokens={max_tokens}")
    sep("═")

    for i, technique in enumerate(techniques, 1):
        prompt = build_prompt(task, technique)
        print(f"\n  [{i}/{len(techniques)}] {technique}...")
        try:
            raw, usage = openai_client.chat(
                provider_key=provider_key,
                model_id=model_id,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"  Ошибка: {e}")
            sys.exit(1)

        parsed, status = parse_response(raw)
        cost = calc_cost(usage, model_dict)
        cost_str = f"{cost:.4f}₽" if cost > 0 else "бесплатно"
        print(f"  Статус: {status} | токены: {usage.get('total_tokens','?')} | {cost_str}")

        results.append({
            "technique": technique,
            "prompt":    prompt,
            "raw":       raw,
            "parsed":    parsed,
            "status":    status,
            "usage":     usage,
            "cost":      cost,
            "metrics":   _metrics(parsed, status),
            "rank":      0,
            "score":     0.0,
        })

    results = compare_all(results)
    print_comparison(results)

    # Диагностика: если все ответы невалидны
    all_invalid = all(r["status"] == "invalid" for r in results)
    if all_invalid:
        print()
        sep("!")
        print("  ВНИМАНИЕ: все техники вернули невалидный JSON.")
        print(f"  Использованная temperature={temperature} слишком высокая для JSON-вывода.")
        print("  Рекомендация: повторите запуск с temperature=0.2")
        sep("!")

    # Предупреждение если итерация zero-shot→few-shot неполная
    has_zero = any(r["technique"] == "zero-shot" for r in results)
    has_few  = any(r["technique"] == "few-shot"  for r in results)
    if not (has_zero and has_few):
        missing = []
        if not has_zero: missing.append("zero-shot")
        if not has_few:  missing.append("few-shot")
        print(f"\n  Совет: для сравнения итерации качества добавьте технику(и): {', '.join(missing)}")

    artifact_path, readme_path = write_artifact(
        task=task,
        provider_name=PROVIDERS[provider_key]["name"],
        model_id=model_id,
        model_label=model_label,
        temperature=temperature,
        max_tokens=max_tokens,
        results=results,
    )
    print(f"\n  Отчёт A/B   → {artifact_path}")
    print(f"  README итог → {readme_path}")


if __name__ == "__main__":
    run()
